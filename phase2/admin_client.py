"""
Step 4 - Admin client (Management user interface).

The same idea as the Phase 1 CLI, but every option is now a gRPC call to the
Coordinator server. Participants are NOT registered here any more: each
participant registers itself from its own process (participant_client.py).

Run:
    python admin_client.py
    python admin_client.py --server 192.168.1.20:50051
"""

import argparse
import sys
import time

import grpc

import fl_pb2 as pb
import fl_pb2_grpc as pb_grpc

MENU = """
===== FL Admin (connected to {server}) =====
1. Create training job
2. Start training job (and watch it)
3. Show job status
0. Exit"""


class AdminClient:
    # 4.1 - Connect to the server
    def __init__(self, address: str):
        self.address = address
        channel = grpc.insecure_channel(address)
        try:
            grpc.channel_ready_future(channel).result(timeout=10)
        except grpc.FutureTimeoutError:
            sys.exit(f"Error: cannot reach the coordinator at {address}. "
                     f"Is the server running? Is the address/firewall correct?")
        self._stub = pb_grpc.CoordinatorStub(channel)

    # 4.2 - Menu loop (same structure as Phase 1)
    def run(self) -> None:
        actions = {"1": self.create_job, "2": self.start_job, "3": self.show_status}
        while True:
            print(MENU.format(server=self.address))
            choice = input("Choose an option: ").strip()
            if choice == "0":
                print("Bye!")
                break
            action = actions.get(choice)
            if action is None:
                print(f"'{choice}' is not a menu option. Type a number from 0 to 3.")
                continue
            # 4.3 - gRPC errors arrive as RpcError (code + message from the server)
            try:
                action()
            except grpc.RpcError as error:
                print(f"Error from server: {error.code().name}: {error.details()}")
            except ValueError as error:
                print(f"Error: {error}")

    # 4.4 - One gRPC call per option
    def create_job(self) -> None:
        text = input("Number of rounds: ").strip()
        if not text.isdigit():
            raise ValueError("Number of rounds must be a positive whole number")
        reply = self._stub.CreateJob(pb.CreateJobRequest(
            config=pb.TrainingConfig(num_rounds=int(text))))
        print(f"Job created: {reply.job_id}")

    def start_job(self) -> None:
        job_id = input("Job id (e.g. job-1): ").strip()
        status = self._stub.StartTraining(pb.JobRequest(job_id=job_id))
        print(f"{job_id} started with participants {list(status.participant_ids)}")
        self._watch(job_id)

    def show_status(self) -> None:
        job_id = input("Job id (e.g. job-1): ").strip()
        self._print_status(self._stub.GetTrainingStatus(pb.JobRequest(job_id=job_id)))

    # 4.5 - Training happens in the participants, so we poll until it ends
    def _watch(self, job_id: str, timeout: float = 60.0) -> None:
        print("Waiting for the participants... (Ctrl+C to stop watching)")
        deadline = time.time() + timeout
        last_round = None
        try:
            while time.time() < deadline:
                status = self._stub.GetTrainingStatus(pb.JobRequest(job_id=job_id))
                if status.status in (pb.COMPLETED, pb.FAILED):
                    self._print_status(status)
                    return
                if status.current_round != last_round:
                    print(f"  round {status.current_round}/{status.num_rounds} running...")
                    last_round = status.current_round
                time.sleep(0.5)
            print("Still running. Are all participants started? Use option 3 to check later.")
        except KeyboardInterrupt:
            print("\nStopped watching (the job keeps running on the server).")

    @staticmethod
    def _print_status(status) -> None:
        print(f"Job:            {status.job_id}")
        print(f"Status:         {pb.JobStatus.Name(status.status)}")
        print(f"Rounds:         {status.num_rounds}")
        print(f"Participants:   {', '.join(status.participant_ids)}")
        print(f"Local results:  {dict(sorted(status.local_results.items()))}")
        print(f"Global weight:  {status.global_weight}")


def main():
    parser = argparse.ArgumentParser(description="Federated Learning admin client")
    parser.add_argument("--server", default="localhost:50051",
                        help="coordinator address host:port (default localhost:50051)")
    AdminClient(parser.parse_args().server).run()


if __name__ == "__main__":
    main()
