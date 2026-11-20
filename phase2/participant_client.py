"""
Step 3 - Participant client (one process per participant).

The participant's data lives ONLY in this process. It registers with the
Coordinator (name only), then repeatedly asks for work:

    GetTrainingTask -> train locally -> SubmitTrainingResult

Run (one terminal per participant):
    python participant_client.py A 8,10,12
    python participant_client.py B 18,20,22
    python participant_client.py C 28,30,32

On another computer, point it to the server's IP:
    python participant_client.py A 8,10,12 --server 192.168.1.20:50051
"""

import argparse
import sys
import time
from pathlib import Path

import grpc

import fl_pb2 as pb
import fl_pb2_grpc as pb_grpc

# 3.1 - Reuse the Phase 1 Participant: the training logic is unchanged
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "phase1"))
from participant import Participant  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Federated Learning participant")
    parser.add_argument("name", help="participant name, e.g. A")
    parser.add_argument("data", help="local data, comma separated, e.g. 8,10,12")
    parser.add_argument("--server", default="localhost:50051",
                        help="coordinator address host:port (default localhost:50051)")
    parser.add_argument("--poll", type=float, default=1.0,
                        help="seconds between two task requests (default 1.0)")
    return parser.parse_args()


def parse_numbers(text: str) -> list[float]:
    try:
        return [float(p) for p in text.split(",") if p.strip()]
    except ValueError:
        sys.exit(f"Error: '{text}' is not a list of numbers")


# 3.2 - Connect and check that the server is reachable
def connect(address: str) -> pb_grpc.CoordinatorStub:
    channel = grpc.insecure_channel(address)
    try:
        grpc.channel_ready_future(channel).result(timeout=10)
    except grpc.FutureTimeoutError:
        sys.exit(f"Error: cannot reach the coordinator at {address}. "
                 f"Is the server running? Is the address/firewall correct?")
    print(f"[client] connected to coordinator at {address}")
    return pb_grpc.CoordinatorStub(channel)


def main():
    args = parse_args()
    data = parse_numbers(args.data)
    stub = connect(args.server)

    # 3.3 - Register: only the NAME is sent, the data stays here
    try:
        reply = stub.RegisterParticipant(pb.RegisterRequest(name=args.name))
    except grpc.RpcError as error:
        sys.exit(f"Error: {error.code().name}: {error.details()}")
    participant = Participant(reply.participant_id, args.name, data)
    print(f"[{args.name}] registered as {reply.participant_id} "
          f"({participant.num_samples} local samples, kept private)")

    # 3.4 - Work loop: ask for a task, train, submit, repeat
    waiting_printed = False
    try:
        while True:
            reply = stub.GetTrainingTask(
                pb.TaskRequest(participant_id=participant.participant_id))

            if not reply.has_task:
                if not waiting_printed:
                    print(f"[{args.name}] waiting for a task... (Ctrl+C to quit)")
                    waiting_printed = True
                time.sleep(args.poll)
                continue

            waiting_printed = False
            task = reply.task
            print(f"[{args.name}] got task: {task.job_id} round {task.round_number} "
                  f"(global weight = {task.global_weight})")

            # 3.5 - Local training with the Phase 1 code
            result = participant.train(task)

            # 3.6 - Send back ONLY the result (dataclass -> protobuf message)
            answer = stub.SubmitTrainingResult(pb.TrainingResult(
                participant_id=result.participant_id,
                job_id=result.job_id,
                round_number=result.round_number,
                weight=result.weight,
                num_samples=result.num_samples,
            ))
            print(f"[{args.name}] submitted result -> {answer.message}")

    except KeyboardInterrupt:
        print(f"\n[{args.name}] stopped")
    except grpc.RpcError as error:
        sys.exit(f"[{args.name}] lost connection to the coordinator: {error.code().name}")


if __name__ == "__main__":
    main()
