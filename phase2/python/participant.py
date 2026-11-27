"""Participant B (Python) of the federated learning framework.

Push model: the participant runs its own gRPC server (ParticipantService), registers
its address with the coordinator and then waits. For every round the coordinator
calls SendTrainingTask; the participant trains on its local data and returns the
result. The local data never leaves this program.

Run:
    python participant.py                                   # interactive setup
    python participant.py --name "Participant B" --data 18,20,22
    python participant.py --name "Participant B" --data-file data/participant-b.json
    python participant.py --help
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent import futures

import grpc

import federated_learning_pb2 as pb
import federated_learning_pb2_grpc as pb_grpc

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_NAME = "Participant B"                                   # this Python program is Participant B
DEFAULT_DATA_FILE = os.path.join("data", "participant-b.json")
DEFAULT_COORDINATOR = os.environ.get("COORDINATOR_ADDRESS", "127.0.0.1:50051")
DEFAULT_HOST = "127.0.0.1"
RPC_TIMEOUT_S = 5.0
MAX_RETRY_DELAY_S = 10.0


class ConfigError(Exception):
    """Invalid user input; the message is meant for the user."""


# ---------------------------------------------------------------- logging

class Logger:
    def __init__(self, name: str):
        self.name = name

    def _line(self, level: str, message: str) -> str:
        prefix = "" if level == "INFO" else f"{level}: "
        return f"[{time.strftime('%H:%M:%S')}] [{self.name}] {prefix}{message}"

    def info(self, message: str) -> None:
        print(self._line("INFO", message), flush=True)

    def warn(self, message: str) -> None:
        print(self._line("WARN", message), file=sys.stderr, flush=True)

    def error(self, message: str) -> None:
        print(self._line("ERROR", message), file=sys.stderr, flush=True)


# ---------------------------------------------------------------- local data and training

def validate_data(values, source: str) -> list:
    if not isinstance(values, list) or not values:
        raise ConfigError(f"Local data from {source} must be a non-empty list of numbers")
    numbers = []
    for value in values:
        if isinstance(value, bool):
            raise ConfigError(f"Local data from {source} contains a value that is not a number: {value!r}")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ConfigError(f"Local data from {source} contains a value that is not a number: {value!r}") from None
        if number != number or number in (float("inf"), float("-inf")):
            raise ConfigError(f"Local data from {source} contains a value that is not a finite number: {value!r}")
        numbers.append(number)
    return numbers


def parse_data_list(text: str) -> list:
    parts = [part.strip() for part in text.split(",")]
    if any(part == "" for part in parts):
        raise ConfigError("Local data contains an empty value (check the commas)")
    return validate_data(parts, "--data")


def read_data_file(path: str, base_dir: str = HERE) -> list:
    full_path = path if os.path.isabs(path) else os.path.join(base_dir, path)
    try:
        with open(full_path, encoding="utf-8") as file:
            content = json.load(file)
    except OSError as error:
        raise ConfigError(f"Cannot read data file {full_path}: {error.strerror}") from None
    except json.JSONDecodeError as error:
        raise ConfigError(f"Data file {full_path} is not valid JSON: {error}") from None
    return validate_data(content, full_path)


class LocalTrainer:
    """Keeps the local data private and trains on it."""

    def __init__(self, local_data: list):
        if not local_data:
            raise ValueError("LocalTrainer needs a non-empty list of numbers")
        self._data = list(local_data)

    @property
    def num_samples(self) -> int:
        return len(self._data)

    def train(self, task: pb.TrainingTask) -> tuple:
        """Simulated training (same as Phase 1): the local model is the mean of the local data.
        The task is received so a real model could start from task.global_weight."""
        return sum(self._data) / len(self._data), len(self._data)


# ---------------------------------------------------------------- gRPC service (called by the coordinator)

class ParticipantServicer(pb_grpc.ParticipantServiceServicer):
    """Answers the coordinator's SendTrainingTask calls."""

    def __init__(self, trainer: LocalTrainer, logger: Logger):
        self._trainer = trainer
        self._log = logger
        self.address = ""                 # set once the server is bound to a port
        self.rounds_trained = 0

    def SendTrainingTask(self, request, context):
        task = request.task
        if not task.job_id or task.round < 1:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Task must have a job_id and a round >= 1")

        self._log.info(f"received {task.job_id} round {task.round} (global weight = {task.global_weight})")
        local_weight, num_samples = self._trainer.train(task)
        self.rounds_trained += 1
        self._log.info(f"trained on {num_samples} samples -> local weight = {local_weight}")

        # only the result leaves the participant, never the data
        return pb.TrainingResult(job_id=task.job_id, participant_id=self.address, round=task.round,
                                 local_weight=local_weight, num_samples=num_samples)


# ---------------------------------------------------------------- the participant

class Participant:
    def __init__(self, name: str, trainer: LocalTrainer, coordinator_address: str,
                 host: str = DEFAULT_HOST, port: int = 0, logger: Logger = None,
                 rpc_timeout_s: float = RPC_TIMEOUT_S, max_retry_delay_s: float = MAX_RETRY_DELAY_S):
        self.name = name
        self.coordinator_address = coordinator_address
        self._host = host
        self._port = port
        self._log = logger or Logger(name)
        self._rpc_timeout_s = rpc_timeout_s
        self._max_retry_delay_s = max_retry_delay_s
        self._stop = threading.Event()
        self._server = None
        self.servicer = ParticipantServicer(trainer, self._log)
        self.address = ""
        self.registered = False

    def start_server(self) -> str:
        """Starts the ParticipantService. Port 0 means: let the system pick a free port."""
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        pb_grpc.add_ParticipantServiceServicer_to_server(self.servicer, self._server)
        port = self._server.add_insecure_port(f"{self._host}:{self._port}")
        if port == 0:
            raise ConfigError(f"Cannot listen on {self._host}:{self._port} (port already in use?)")
        self._server.start()
        self.address = self.servicer.address = f"{self._host}:{port}"
        self._log.info(f"ParticipantService listening on {self.address}")
        return self.address

    def register(self) -> bool:
        """Registers with the coordinator; keeps retrying (with backoff) while it is not reachable."""
        delay = 1.0
        while not self._stop.is_set():
            try:
                with grpc.insecure_channel(self.coordinator_address) as channel:
                    stub = pb_grpc.CoordinatorServiceStub(channel)
                    stub.RegisterParticipant(
                        pb.RegisterParticipantRequest(participant_ip_addr=self.address, name=self.name),
                        timeout=self._rpc_timeout_s)
                self.registered = True
                self._log.info(f"registered with the coordinator at {self.coordinator_address} "
                               f"- waiting for training tasks")
                return True
            except grpc.RpcError as error:
                if error.code() not in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
                    raise ConfigError(f"Coordinator refused the registration: {error.details()}") from None
                self._log.warn(f"coordinator at {self.coordinator_address} not reachable "
                               f"- retrying in {delay:g} s")
                self._stop.wait(delay)
                delay = min(delay * 2, self._max_retry_delay_s)
        return False

    def run(self) -> None:
        """Starts the server, registers and serves until stop() or Ctrl+C."""
        self.start_server()
        try:
            if self.register():
                while not self._stop.wait(0.5):       # short waits so Ctrl+C works on Windows
                    pass
        finally:
            self.shutdown()

    def stop(self) -> None:
        self._stop.set()

    def shutdown(self) -> None:
        self._stop.set()
        if self._server is not None:
            self._server.stop(grace=1).wait()
            self._server = None
            self._log.info(f"stopped after {self.servicer.rounds_trained} round(s)")


# ---------------------------------------------------------------- configuration

ADDRESS_PATTERN = re.compile(r"^[^\s:]+:\d+$")


def interview(ask=input, out=print):
    """Asks for name, data and coordinator address. Returns a config dict, or None if cancelled."""

    def ask_until_valid(question, check):
        while True:
            answer = ask(question).strip()
            try:
                return check(answer)
            except ConfigError as error:
                out(f"  {error} - please try again.")

    def check_data(answer):
        answer = answer or DEFAULT_DATA_FILE
        if answer.lower().endswith(".json"):
            return read_data_file(answer)
        return parse_data_list(answer)

    def check_address(answer):
        value = answer or DEFAULT_COORDINATOR
        if not ADDRESS_PATTERN.match(value):
            raise ConfigError(f'"{value}" is not a host:port address')
        return value

    out("")
    out("===== Federated Learning - Participant setup (Python) =====")
    out("Your data stays on this machine. Only the training result is sent to the coordinator.")
    out("Press Enter to accept the value in [brackets].")
    out("")
    name = ask_until_valid(f"Participant name [{DEFAULT_NAME}]: ", lambda a: a or DEFAULT_NAME)
    data = ask_until_valid("Local data - numbers separated by commas (e.g. 18,20,22) "
                           f"or a .json file [{DEFAULT_DATA_FILE}]: ", check_data)
    coordinator = ask_until_valid(f"Coordinator address [{DEFAULT_COORDINATOR}]: ", check_address)

    out("")
    out("Summary:")
    out(f"  Name:        {name}")
    out(f"  Local data:  {', '.join(f'{v:g}' for v in data)}  ({len(data)} samples)")
    out(f"  Coordinator: {coordinator}")
    if ask("Register with the coordinator now? [Y/n]: ").strip().lower() in ("n", "no"):
        return None
    out("")
    return {"name": name, "data": data, "coordinator": coordinator, "host": DEFAULT_HOST, "port": 0}


def port_number(text: str) -> int:
    value = int(text)
    if not 0 <= value <= 65535:
        raise argparse.ArgumentTypeError("must be between 0 and 65535")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="participant.py",
        description="Participant B (Python) of the federated learning framework. "
                    "Without options it asks for its settings interactively.")
    parser.add_argument("-n", "--name", help=f'participant name (default "{DEFAULT_NAME}")')
    source = parser.add_mutually_exclusive_group()
    source.add_argument("-d", "--data", help="local data as comma-separated numbers, e.g. 18,20,22")
    source.add_argument("-f", "--data-file", help=f"local data as a JSON array file (default {DEFAULT_DATA_FILE})")
    parser.add_argument("-c", "--coordinator", default=DEFAULT_COORDINATOR,
                        help=f"coordinator host:port (default {DEFAULT_COORDINATOR}, env COORDINATOR_ADDRESS)")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"host the coordinator uses to reach this participant (default {DEFAULT_HOST})")
    parser.add_argument("-p", "--port", type=port_number, default=0,
                        help="port of this participant's service (default 0 = any free port)")
    return parser


def config_from_args(args) -> dict:
    data = parse_data_list(args.data) if args.data else read_data_file(args.data_file or DEFAULT_DATA_FILE)
    if not ADDRESS_PATTERN.match(args.coordinator):
        raise ConfigError(f'--coordinator "{args.coordinator}" is not a host:port address')
    return {"name": (args.name or DEFAULT_NAME).strip() or DEFAULT_NAME, "data": data,
            "coordinator": args.coordinator, "host": args.host, "port": args.port}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        if not argv and sys.stdin.isatty():
            config = interview()
            if config is None:
                print("Not registered. Bye!")
                return 0
        else:
            config = config_from_args(build_parser().parse_args(argv))

        logger = Logger(config["name"])
        participant = Participant(config["name"], LocalTrainer(config["data"]), config["coordinator"],
                                  host=config["host"], port=config["port"], logger=logger)
        logger.info(f"starting with {len(config['data'])} samples")
        participant.run()
        return 0
    except ConfigError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nStopped")
        return 0


if __name__ == "__main__":
    sys.exit(main())
