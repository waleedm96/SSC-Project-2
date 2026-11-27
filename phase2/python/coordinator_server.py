"""Coordinator Service (Python) - the gRPC server of the federated learning framework.

Push model: participants register the address of their own ParticipantService.
When a job is started, the coordinator sends each round's task to every participant
(SendTrainingTask), collects the results and aggregates them with FedAvg.
"""

import threading
import time
from concurrent import futures

import grpc

import federated_learning_pb2 as pb
import federated_learning_pb2_grpc as pb_grpc

ADDRESS = "127.0.0.1:50051"
TASK_TIMEOUT_S = 30.0          # how long one participant may take to train one round


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] [Coordinator] {message}", flush=True)


class Aggregator:
    """FedAvg: weighted average of the local weights (same formula as Phase 1)."""

    def aggregate(self, results: list) -> float:
        total_samples = sum(r.num_samples for r in results)
        weighted_sum = sum(r.local_weight * r.num_samples for r in results)
        return weighted_sum / total_samples


class CoordinatorServicer(pb_grpc.CoordinatorServiceServicer):

    def __init__(self, task_timeout_s: float = TASK_TIMEOUT_S):
        self._lock = threading.Lock()                 # protects _participants and _jobs
        self._participants: dict[str, str] = {}       # "127.0.0.1:50101" -> "Participant A"
        self._jobs: dict[str, pb.TrainingJob] = {}    # "job-1" -> TrainingJob message
        self._aggregator = Aggregator()
        self._task_timeout_s = task_timeout_s

    # ------------------------------------------------------------ called by participants

    def RegisterParticipant(self, request, context):
        ip_address = request.participant_ip_addr.strip()
        name = request.name.strip()
        if not ip_address:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Participant ip address is empty")
        if not name:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Participant name is empty")

        with self._lock:
            again = ip_address in self._participants
            self._participants[ip_address] = name

        log(f"RegisterParticipant: '{name}' {'registered again' if again else 'registered'} at {ip_address}")
        return pb.RegisterParticipantReply(participant_ip_addr=ip_address)

    # ------------------------------------------------------------ called by the management client

    def ListParticipants(self, request, context):
        with self._lock:
            participants = [pb.ParticipantInfo(participant_ip_addr=ip, name=name)
                            for ip, name in self._participants.items()]
        return pb.ListParticipantsReply(participants=participants)

    def CreateJob(self, request, context):
        num_rounds = request.config.num_rounds or 1          # 0 means "not set" -> default 1
        if num_rounds < 1:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "num_rounds must be at least 1")

        with self._lock:
            if not self._participants:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION,
                              "Register at least one participant before creating a job")

            job_id = f"job-{len(self._jobs) + 1}"
            job = pb.TrainingJob(
                job_id=job_id,
                config=pb.TrainingConfig(num_rounds=num_rounds, initial_weight=request.config.initial_weight),
                participant_ids=list(self._participants.keys()),
                status=pb.CREATED,
                global_weight=request.config.initial_weight,
            )
            self._jobs[job_id] = job

        log(f"CreateJob: {job_id} created with participants {list(job.participant_ids)}, "
            f"{num_rounds} round(s)")
        return pb.CreateJobReply(job_id=job_id)

    def StartTraining(self, request, context):
        with self._lock:
            job = self._get_job(request.job_id, context)
            if job.status != pb.CREATED:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION,
                              f"{job.job_id} cannot be started (status is {pb.JobStatus.Name(job.status)})")
            job.status = pb.RUNNING
            job.current_round = 1

        # Training runs in the background, so this call returns at once;
        # the management client follows the progress with GetTrainingStatus.
        log(f"StartTraining: {job.job_id} is RUNNING")
        threading.Thread(target=self._run_job, args=(job.job_id,), name=f"train-{job.job_id}", daemon=True).start()
        return pb.StartTrainingReply(started=True, message=f"{job.job_id} started")

    def GetTrainingStatus(self, request, context):
        with self._lock:
            job = self._get_job(request.job_id, context)
            reply = pb.TrainingJob()
            reply.CopyFrom(job)          # send a copy, so the job can keep changing safely
        return reply

    # ------------------------------------------------------------ training (background thread)

    def _run_job(self, job_id: str) -> None:
        try:
            finished = False
            while not finished:
                with self._lock:
                    job = self._jobs[job_id]
                    task = pb.TrainingTask(job_id=job.job_id, round=job.current_round,
                                           global_weight=job.global_weight, config=job.config)
                    addresses = list(job.participant_ids)

                log(f"{job_id} round {task.round}/{task.config.num_rounds}: sending task to "
                    f"{len(addresses)} participant(s) (global weight = {task.global_weight})")
                results = self._collect_results(task, addresses)

                with self._lock:
                    if not results:
                        job.status = pb.FAILED
                        log(f"{job_id} FAILED - no participant returned a result in round {task.round}")
                        return
                    for result in results:
                        job.results.add().CopyFrom(result)
                    finished = self._finish_round(job, results, expected=len(addresses))
        except Exception as error:  # never leave a job stuck in RUNNING
            with self._lock:
                self._jobs[job_id].status = pb.FAILED
            log(f"{job_id} FAILED - unexpected error: {error!r}")

    def _collect_results(self, task: pb.TrainingTask, addresses: list) -> list:
        """Sends the task to all participants at the same time and keeps the valid results."""
        with futures.ThreadPoolExecutor(max_workers=len(addresses)) as pool:
            replies = list(pool.map(lambda address: self._send_task(address, task), addresses))
        return [r for r in replies if r is not None]

    def _send_task(self, address: str, task: pb.TrainingTask):
        try:
            with grpc.insecure_channel(address) as channel:
                stub = pb_grpc.ParticipantServiceStub(channel)
                result = stub.SendTrainingTask(pb.TrainingTaskRequest(task=task), timeout=self._task_timeout_s)
        except grpc.RpcError as error:
            log(f"Participant {address} did not answer ({error.code().name}) - skipped in round {task.round}")
            return None

        problem = self._check_result(result, task)
        if problem:
            log(f"Result from {address} rejected: {problem}")
            return None

        result.participant_id = address    # the coordinator knows who it asked
        log(f"SendTrainingTask: {address} -> local weight = {result.local_weight} "
            f"({result.num_samples} samples)")
        return result

    @staticmethod
    def _check_result(result: pb.TrainingResult, task: pb.TrainingTask):
        if result.job_id != task.job_id:
            return f"wrong job ({result.job_id!r} instead of {task.job_id!r})"
        if result.round != task.round:
            return f"wrong round ({result.round} instead of {task.round})"
        if result.num_samples <= 0:
            return "num_samples must be positive"
        return None

    def _finish_round(self, job: pb.TrainingJob, results: list, expected: int) -> bool:
        """Aggregates one round. Returns True when the job is finished. Caller holds the lock."""
        job.global_weight = self._aggregator.aggregate(results)

        values = " + ".join(f"{r.local_weight} x {r.num_samples}" for r in results)
        total = sum(r.num_samples for r in results)
        log(f"Aggregation round {job.current_round} ({len(results)}/{expected} participants): "
            f"({values}) / {total} -> global weight = {job.global_weight}")

        if job.current_round < job.config.num_rounds:
            job.current_round += 1
            return False
        job.status = pb.COMPLETED
        log(f"{job.job_id} COMPLETED - final global weight = {job.global_weight}")
        return True

    def _get_job(self, job_id, context) -> pb.TrainingJob:
        if job_id not in self._jobs:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Unknown job: {job_id}")
        return self._jobs[job_id]


def create_server(address: str = ADDRESS, task_timeout_s: float = TASK_TIMEOUT_S) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb_grpc.add_CoordinatorServiceServicer_to_server(CoordinatorServicer(task_timeout_s), server)
    server.add_insecure_port(address)
    return server


def serve() -> None:
    server = create_server()
    server.start()
    log(f"Coordinator Service started on {ADDRESS} - waiting for requests (Ctrl+C to stop)")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        log("Stopping")
        server.stop(grace=0)


if __name__ == "__main__":
    serve()
