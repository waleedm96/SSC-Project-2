"""Management Client (CLI)"""
import sys
import grpc

import federated_learning_pb2 as pb
import federated_learning_pb2_grpc as pb_grpc

DEFAULT_ADDRESS = "127.0.0.1:50051"
TIMEOUT_SECONDS = 5.0


class CoordinatorClient:
    """gRPC wrapper for the CoordinatorService."""

    def __init__(self, address: str = DEFAULT_ADDRESS):
        self.address = address
        self._channel = grpc.insecure_channel(address)
        self._stub = pb_grpc.CoordinatorServiceStub(self._channel)

    def close(self) -> None:
        self._channel.close()

    def list_participants(self) -> list:
        request = pb.ListParticipantsRequest()
        reply = self._stub.ListParticipants(request, timeout=TIMEOUT_SECONDS)
        return list(reply.participants)

    def create_job(self, num_rounds: int, initial_weight: float) -> str:
        config = pb.TrainingConfig(
            num_rounds=num_rounds,
            initial_weight=initial_weight,
        )
        request = pb.CreateJobRequest(config=config)
        reply = self._stub.CreateJob(request, timeout=TIMEOUT_SECONDS)
        return reply.job_id

    def start_training(self, job_id: str) -> tuple[bool, str]:
        request = pb.StartTrainingRequest(job_id=job_id)
        reply = self._stub.StartTraining(request, timeout=TIMEOUT_SECONDS)
        return reply.started, reply.message
    def get_training_status(self, job_id: str) -> pb.TrainingJob:
        request = pb.TrainingStatusRequest(job_id=job_id)
        return self._stub.GetTrainingStatus(request, timeout=TIMEOUT_SECONDS)


def handle_rpc_error(err: grpc.RpcError) -> None:
    print(f"[gRPC Error] {err.code().name}: {err.details()}")

def print_job(job: pb.TrainingJob) -> None:
    status_name = pb.JobStatus.Name(job.status)
    print(f"\n--- Job {job.job_id} ---")
    print(f"  Status        : {status_name}")
    print(f"  Round         : {job.current_round} / {job.config.num_rounds}")
    print(f"  Initial weight: {job.config.initial_weight}")
    print(f"  Global weight : {job.global_weight}")
    print(f"  Participants  : {', '.join(job.participant_ids)}")

    if not job.results:
        print("  Results       : (none yet)")
    else:
        print("  Results:")
        print(f"    {'Round':<7} {'Participant':<13} {'Local Weight':<14} {'Samples':<8}")
        for r in job.results:
            print(
                f"    {r.round:<7} {r.participant_id:<13} "
                f"{r.local_weight:<14.4f} {r.num_samples:<8}"
            )

def main() -> None:
    address = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADDRESS
    client = CoordinatorClient(address)
    print(f"Connected to Coordinator at {address}")

    try:
        while True:
            print("\n=== Federated Learning Management CLI ===")
            print("4. Check training job status")
            print("3. Start a training job")
            print("2. Create a new training job")
            print("1. List registered participants")
            print("0. Exit")
            choice = input("Select an option: ").strip()

            try:
                if choice == "1":
                    participants = client.list_participants()
                    if not participants:
                        print("No participants here :>")
                    else:
                        print(f"\nRegistered participants ({len(participants)}):")
                        for p in participants:
                            print(f"  - {p.participant_id}: {p.name}")
                elif choice == "2":
                    try:
                        num_rounds = int(input("Number of rounds (default 1): ").strip() or "1")
                        initial_weight = float(input("Initial global weight (default 0.0): ").strip() or "0.0")
                    except ValueError:
                        print("Not a number. Enter intergers or floats only.")
                        continue
                    job_id = client.create_job(num_rounds, initial_weight)
                    print(f"Created job: {job_id}")
                elif choice == "3":
                    job_id = input("Job ID to start (e.g. job-1): ").strip()
                    if not job_id:
                        print("Job ID cannot be empty.")
                        continue
                    started, message = client.start_training(job_id)
                    print(f"StartTraining -> started={started}, message='{message}'")
                elif choice == "4":
                    job_id = input("Job ID to check (e.g. job-1): ").strip()
                    if not job_id:
                        print("Job ID cannot be empty.")
                        continue
                    job = client.get_training_status(job_id)
                    print_job(job)
                elif choice == "0":
                    print("Bye bye!")
                    break
                else:
                    print("Invalid option. Try another bro.")
            except grpc.RpcError as err:
                handle_rpc_error(err)
    finally:
        client.close()


if __name__ == "__main__":
    main()
