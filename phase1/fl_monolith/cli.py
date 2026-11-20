"""CLI: text menu for the administrator. It only reads input and calls the coordinator."""

from models import TrainingConfig
from coordinator import Coordinator


class CLI:
    def __init__(self, coordinator: Coordinator):
        self._coordinator = coordinator

    def run(self) -> None:
        while True:
            self._show_menu()
            choice = input("Choose an option: ").strip()

            try:
                if choice == "1":
                    self._register_participant()
                elif choice == "2":
                    self._load_example()
                elif choice == "3":
                    self._create_job()
                elif choice == "4":
                    self._start_job()
                elif choice == "5":
                    self._show_status()
                elif choice == "0":
                    print("Bye!")
                    break
                else:
                    print("Invalid option, try again.")
            except (ValueError, KeyError) as error:
                print(f"Error: {error.args[0]}")

    def _show_menu(self) -> None:
        print()
        print("===== Minimal Federated Learning Framework =====")
        print("1. Register participant")
        print("2. Load example participants (A, B, C)")
        print("3. Create training job")
        print("4. Start training job")
        print("5. Show job status")
        print("0. Exit")

    def _register_participant(self) -> None:
        name = input("Participant name: ").strip()
        text = input("Local data (comma separated, e.g. 8,10,12): ")
        data = [float(value) for value in text.split(",")]
        self._coordinator.register_participant(name, data)

    def _load_example(self) -> None:
        self._coordinator.register_participant("Participant A", [8, 10, 12])
        self._coordinator.register_participant("Participant B", [18, 20, 22])
        self._coordinator.register_participant("Participant C", [28, 30, 32])

    def _create_job(self) -> None:
        rounds = int(input("Number of rounds: ") or "1")
        job_id = self._coordinator.create_job(TrainingConfig(num_rounds=rounds))
        print(f"Job created: {job_id}")

    def _start_job(self) -> None:
        job_id = input("Job id (e.g. job-1): ").strip()
        self._coordinator.start_job(job_id)

    def _show_status(self) -> None:
        job_id = input("Job id (e.g. job-1): ").strip()
        job = self._coordinator.get_status(job_id)
        print(f"\nJob:           {job.job_id}")
        print(f"Status:        {job.status.value}")
        print(f"Participants:  {', '.join(job.participant_ids)}")
        print(f"Rounds:        {job.current_round}/{job.config.num_rounds}")
        print(f"Global weight: {job.global_weight}")
        if job.results:
            print("Local results:")
            for r in job.results:
                print(f"  round {r.round} | {r.participant_id} | weight = {r.local_weight} | samples = {r.num_samples}")
