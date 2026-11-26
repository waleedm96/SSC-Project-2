"""Coordinator Service (Python) - the gRPC server of the federated learning framework."""

import threading
import time
from concurrent import futures

import grpc

import federated_learning_pb2 as pb
import federated_learning_pb2_grpc as pb_grpc

ADDRESS = "127.0.0.1:50051"


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] [Coordinator] {message}", flush=True)


class Aggregator:
    """FedAvg: weighted average of the local weights (same formula as Phase 1)."""

    def aggregate(self, results: list) -> float:
        total_samples = sum(r.num_samples for r in results)
        weighted_sum = sum(r.local_weight * r.num_samples for r in results)
        return weighted_sum / total_samples


class CoordinatorServicer(pb_grpc.CoordinatorServiceServicer):

    def __init__(self):
        self._lock = threading.Lock()                 # one request at a time may change the data
        self._participants: dict[str, str] = {}       # "192.88.168.12" -> "Participant A"
        self._jobs: dict[str, pb.TrainingJob] = {}    # "job-1" -> TrainingJob message
        self._round_results: dict[str, dict] = {}     # "job-1" -> {"p1": TrainingResult, ...} for the current round
        self._aggregator = Aggregator()

  #participants funcations 

    def RegisterParticipant(self, request, context):
        ip_address = request.participant_ip_addr.strip()
        name = request.name.strip()
        if not ip_address:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Participant ip address is empty")
        if not name:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Participant name is empty")

        with self._lock:
            self._participants[ip_address] = name

        log(f"RegisterParticipant: '{name}' registered at {ip_address}")
        return pb.RegisterParticipantReply(participant_ip_addr=ip_address)

    # def GetTrainingTask(self, request, context):
    #     participant_id = request.participant_id
    #     with self._lock:
    #         if participant_id not in self._participants:
    #             context.abort(grpc.StatusCode.NOT_FOUND, f"Unknown participant: {participant_id}")

    #         for job in self._jobs.values():
    #             waiting_for_me = (job.status == pb.RUNNING
    #                               and participant_id in job.participant_ids
    #                               and participant_id not in self._round_results[job.job_id])
    #             if waiting_for_me:
    #                 task = pb.TrainingTask(job_id=job.job_id, round=job.current_round,
    #                                        global_weight=job.global_weight, config=job.config)
    #                 log(f"GetTrainingTask: sending {job.job_id} round {job.current_round} "
    #                     f"to {participant_id} (global weight = {job.global_weight})")
    #                 return pb.TrainingTaskReply(has_task=True, task=task)

    #     return pb.TrainingTaskReply(has_task=False)

    # def SubmitTrainingResult(self, request, context):
    #     with self._lock:
    #         job = self._get_job(request.job_id, context)

    #         if job.status != pb.RUNNING:
    #             return pb.SubmitResultReply(accepted=False, message=f"{job.job_id} is not running")
    #         if request.participant_id not in job.participant_ids:
    #             return pb.SubmitResultReply(accepted=False, message="Participant is not part of this job")
    #         if request.round != job.current_round:
    #             return pb.SubmitResultReply(accepted=False, message=f"Wrong round (current is {job.current_round})")
    #         if request.num_samples <= 0:
    #             return pb.SubmitResultReply(accepted=False, message="num_samples must be positive")

    #         received = self._round_results[job.job_id]
    #         if request.participant_id in received:
    #             return pb.SubmitResultReply(accepted=False, message="Result already submitted for this round")

    #         received[request.participant_id] = request
    #         job.results.add().CopyFrom(request)
    #         log(f"SubmitTrainingResult: {request.participant_id} -> local weight = {request.local_weight} "
    #             f"({len(received)}/{len(job.participant_ids)} results for round {job.current_round})")

    #         if len(received) == len(job.participant_ids):
    #             self._finish_round(job)

    #     return pb.SubmitResultReply(accepted=True, message="Result accepted")

#client part

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
        #with self._lock:
        job = self._get_job(request.job_id, context)
        if job.status != pb.CREATED:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION,
                            f"{job.job_id} cannot be started (status is {pb.JobStatus.Name(job.status)})")

        job.status = pb.RUNNING
        job.current_round = 1
        self._round_results[job.job_id] = {}

        log(f"StartTraining: {job.job_id} is RUNNING, round 1")
        
        for r in range(job.config.num_rounds) : 
            print("-------- Round : ", r )

            received = {}

            #Send tasks to participants
            for client in self._participants.keys() :
                print("__Client : ", client)
                try : 
                    with grpc.insecure_channel(client) as channel: 
                        print(job)

                        stub = pb_grpc.ParticipantServiceStub(channel)
                        
                        task = pb.TrainingTask(job_id=job.job_id, round=job.current_round,
                            global_weight=job.global_weight, config=job.config)
                        request = pb.TrainingTaskRequest(task=task)

                        results = stub.SendTrainingTask(request)
                        received[results.participant_id] = results

                        log(f"SubmitTrainingResult: {results.participant_id} -> local weight = {results.local_weight} "
                        f"({len(received)}/{len(job.participant_ids)} results for round {job.current_round})")
                except grpc._channel._InactiveRpcError as e : 
                    #print("HERE's the exception : ", type(e), e)
                    log(f"Client {client} is unreachable")
                except Exception as e : 
                    print(f"ERROR {type(e)} : {e}")

            print("HERE")
            #We update the round results
            self._round_results[job.job_id] = received
            self._finish_round(job=job)

        log(f"{job.job_id} is finished, final results are : {job.global_weight}")
        return pb.StartTrainingReply(started=True, message=f"{job.job_id} finished")

    def GetTrainingStatus(self, request, context):
        with self._lock:
            job = self._get_job(request.job_id, context)
            reply = pb.TrainingJob()
            reply.CopyFrom(job)          # send a copy, so the job can keep changing safely
        return reply


    def _get_job(self, job_id, context) -> pb.TrainingJob:
        if job_id not in self._jobs:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Unknown job: {job_id}")
        return self._jobs[job_id]

    def _finish_round(self, job: pb.TrainingJob) -> None:
        log("bullshit")
        results = list(self._round_results[job.job_id].values())
        job.global_weight = self._aggregator.aggregate(results)

        log("yep")
        values = " + ".join(str(r.local_weight) for r in results)
        log(f"Aggregation: ({values}) / {len(results)} -> global weight = {job.global_weight}")
        log("yep2")

        if job.current_round < job.config.num_rounds:
            job.current_round += 1
            self._round_results[job.job_id] = {}
            log(f"{job.job_id}: starting round {job.current_round}")
        else:
            job.status = pb.COMPLETED
            log(f"{job.job_id} COMPLETED - final global weight = {job.global_weight}")


def create_server(address: str = ADDRESS) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb_grpc.add_CoordinatorServiceServicer_to_server(CoordinatorServicer(), server)
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
