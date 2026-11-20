"""
Step 2 - Coordinator Service (gRPC server).

Phase 1: the Coordinator called participant.train() directly (same process).
Phase 2: the Coordinator is a server. Participants and the admin are separate
         programs that call it over the network.

Because participants now live in other processes, the server cannot "call"
them. Instead they ask for work (GetTrainingTask) and send their result back
(SubmitTrainingResult). When all results of a round have arrived, the server
aggregates them (FedAvg) and opens the next round.

Run with:  python coordinator_server.py          (default port 50051)
"""

import sys
import threading
from concurrent import futures
from pathlib import Path

import grpc

import fl_pb2 as pb
import fl_pb2_grpc as pb_grpc

# 2.1 - Reuse the Phase 1 core logic unchanged (Aggregator, JobManager, models)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "phase1"))
from aggregator import Aggregator                    # noqa: E402
from job_manager import JobManager                   # noqa: E402
from models import JobStatus, TrainingConfig         # noqa: E402

# Phase 1 enum  <->  Protobuf enum
STATUS_TO_PROTO = {
    JobStatus.CREATED: pb.CREATED,
    JobStatus.RUNNING: pb.RUNNING,
    JobStatus.COMPLETED: pb.COMPLETED,
    JobStatus.FAILED: pb.FAILED,
}


class CoordinatorService(pb_grpc.CoordinatorServicer):
    def __init__(self):
        # 2.2 - State (all in memory, like Phase 1)
        self._participants: dict[str, str] = {}     # participant_id -> name (NO data!)
        self._next_participant = 1
        self._job_manager = JobManager()
        self._aggregator = Aggregator()
        self._current_round: dict[str, int] = {}    # job_id -> round in progress
        self._received: dict[str, dict] = {}        # job_id -> {participant_id: result}

        # 2.3 - gRPC answers several clients at the same time (threads),
        #       so every access to the state is protected by a lock.
        self._lock = threading.Lock()

    # ------------------------------------------------------------ admin RPCs

    # 2.4 - RegisterParticipant: only a name arrives, the data stays local
    def RegisterParticipant(self, request, context):
        with self._lock:
            name = request.name.strip()
            if not name:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Name cannot be empty")
            if name in self._participants.values():
                context.abort(grpc.StatusCode.ALREADY_EXISTS,
                              f"A participant named '{name}' is already registered")
            pid = f"p{self._next_participant}"
            self._next_participant += 1
            self._participants[pid] = name
            print(f"[Coordinator] registered {name} as {pid}")
            return pb.RegisterReply(participant_id=pid)

    # 2.5 - CreateJob: a job with all registered participants
    def CreateJob(self, request, context):
        with self._lock:
            config = TrainingConfig(num_rounds=request.config.num_rounds)
            try:
                job = self._job_manager.create(config, list(self._participants))
            except ValueError as error:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(error))
            print(f"[Coordinator] created {job.job_id} with participants {job.participant_ids}")
            return pb.CreateJobReply(job_id=job.job_id)

    # 2.6 - StartTraining: CREATED -> RUNNING, open round 1
    def StartTraining(self, request, context):
        with self._lock:
            job = self._get_job(request.job_id, context)
            if job.status != JobStatus.CREATED:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION,
                              f"{job.job_id} is {job.status.value}, "
                              f"it can only start when CREATED")
            self._job_manager.update_status(job.job_id, JobStatus.RUNNING)
            self._open_round(job, 1)
            return self._status_reply(job)

    # 2.7 - GetTrainingStatus: what the admin sees
    def GetTrainingStatus(self, request, context):
        with self._lock:
            return self._status_reply(self._get_job(request.job_id, context))

    # ------------------------------------------------------ participant RPCs

    # 2.8 - GetTrainingTask: "do you have work for me?"
    def GetTrainingTask(self, request, context):
        with self._lock:
            pid = request.participant_id
            if pid not in self._participants:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Unknown participant '{pid}'")

            for job_id, round_number in self._current_round.items():
                job = self._job_manager.get(job_id)
                waiting_for_me = (job.status == JobStatus.RUNNING
                                  and pid in job.participant_ids
                                  and pid not in self._received[job_id])
                if waiting_for_me:
                    task = pb.TrainingTask(job_id=job_id, round_number=round_number,
                                           global_weight=job.global_weight)
                    return pb.TaskReply(has_task=True, task=task)

            return pb.TaskReply(has_task=False)  # nothing to do right now

    # 2.9 - SubmitTrainingResult: collect results, aggregate when complete
    def SubmitTrainingResult(self, request, context):
        with self._lock:
            job = self._get_job(request.job_id, context)
            pid = request.participant_id

            # validate the result before accepting it
            if job.status != JobStatus.RUNNING:
                return pb.SubmitReply(accepted=False, message=f"{job.job_id} is not running")
            if pid not in job.participant_ids:
                return pb.SubmitReply(accepted=False, message=f"{pid} is not part of {job.job_id}")
            if request.round_number != self._current_round[job.job_id]:
                return pb.SubmitReply(accepted=False, message="Wrong round number")
            if pid in self._received[job.job_id]:
                return pb.SubmitReply(accepted=False, message="Result already submitted")

            received = self._received[job.job_id]
            received[pid] = request
            print(f"[Coordinator] {job.job_id} round {request.round_number}: "
                  f"result from {pid} ({len(received)}/{len(job.participant_ids)})")

            if len(received) == len(job.participant_ids):
                self._finish_round(job)
            return pb.SubmitReply(accepted=True, message="Result received")

    # --------------------------------------------------------------- helpers

    def _get_job(self, job_id, context):
        try:
            return self._job_manager.get(job_id)
        except KeyError as error:
            context.abort(grpc.StatusCode.NOT_FOUND, str(error.args[0]))

    def _open_round(self, job, round_number):
        self._current_round[job.job_id] = round_number
        self._received[job.job_id] = {}
        print(f"[Coordinator] ---- {job.job_id} round {round_number} ---- "
              f"waiting for {len(job.participant_ids)} participants "
              f"(global weight = {job.global_weight})")

    # 2.10 - All results arrived: FedAvg, then next round or COMPLETED
    def _finish_round(self, job):
        results = list(self._received[job.job_id].values())
        job.results.extend(results)
        job.global_weight = self._aggregator.aggregate(results)  # Phase 1 code!

        round_number = self._current_round[job.job_id]
        if round_number < job.config.num_rounds:
            self._open_round(job, round_number + 1)
        else:
            del self._current_round[job.job_id]
            self._job_manager.update_status(job.job_id, JobStatus.COMPLETED)
            print(f"[Coordinator] {job.job_id} finished, global weight = {job.global_weight}")

    def _status_reply(self, job):
        return pb.StatusReply(
            job_id=job.job_id,
            status=STATUS_TO_PROTO[job.status],
            num_rounds=job.config.num_rounds,
            current_round=self._current_round.get(job.job_id, 0),
            participant_ids=job.participant_ids,
            local_results={r.participant_id: r.weight for r in job.results},
            global_weight=job.global_weight,
        )


# 2.11 - Start the server and keep it running
def serve(port: int = 50051) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb_grpc.add_CoordinatorServicer_to_server(CoordinatorService(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"[Coordinator] gRPC server listening on port {port} (Ctrl+C to stop)")
    return server


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 50051
    server = serve(port)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n[Coordinator] shutting down")
        server.stop(grace=1)
