"""
Step 6a - CLI (text menu for the Administrator).

The CLI only reads input and calls the Coordinator. It contains NO
Federated Learning logic. In Phase 2 it becomes the Management Client
(a separate gRPC client process).
"""

from coordinator import Coordinator
from models import TrainingConfig

MENU = """
===== Minimal Federated Learning Framework =====
1. Register participant
2. Load example participants (A, B, C)
3. Create training job
4. Start training job
5. Show job status
0. Exit"""

EXAMPLE_PARTICIPANTS = {
    "A": [8, 10, 12],
    "B": [18, 20, 22],
    "C": [28, 30, 32],
}


class CLI:
    def __init__(self, coordinator: Coordinator):
        self._coordinator = coordinator

    # 6.1 - The main loop: show menu -> read choice -> run action
    def run(self) -> None:
        actions = {
            "1": self._register_participant,
            "2": self._load_example,
            "3": self._create_job,
            "4": self._start_job,
            "5": self._show_status,
        }
        while True:
            print(MENU)
            choice = input("Choose an option: ").strip()
            if choice == "0":
                print("Bye!")
                break
            action = actions.get(choice)
            if action is None:
                print(f"'{choice}' is not a menu option. Type a number from 0 to 5.")
                continue
            # 6.2 - One error must not crash the whole program
            try:
                action()
            except (ValueError, KeyError, RuntimeError) as error:
                print(f"Error: {error}")

    # 6.3 - Convert text "8,10,12" into numbers [8.0, 10.0, 12.0]
    @staticmethod
    def _parse_numbers(text: str) -> list[float]:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        try:
            return [float(p) for p in parts]
        except ValueError:
            raise ValueError(f"'{text}' is not a list of numbers")

    # 6.4 - One small method per menu option
    def _register_participant(self) -> None:
        name = input("Participant name: ").strip()
        if not name:
            raise ValueError("Name cannot be empty")
        data = self._parse_numbers(input("Local data (comma separated, e.g. 8,10,12): "))
        self._coordinator.register_participant(name, data)

    def _load_example(self) -> None:
        for name, data in EXAMPLE_PARTICIPANTS.items():
            self._coordinator.register_participant(name, data)

    def _create_job(self) -> None:
        text = input("Number of rounds: ").strip()
        if not text.isdigit():
            raise ValueError("Number of rounds must be a positive whole number")
        job_id = self._coordinator.create_job(TrainingConfig(num_rounds=int(text)))
        print(f"Job created: {job_id}")

    def _start_job(self) -> None:
        job_id = input("Job id (e.g. job-1): ").strip()
        self._coordinator.start_job(job_id)

    def _show_status(self) -> None:
        job_id = input("Job id (e.g. job-1): ").strip()
        status = self._coordinator.get_status(job_id)
        print(f"Job:            {status['job_id']}")
        print(f"Status:         {status['status']}")
        print(f"Rounds:         {status['rounds']}")
        print(f"Participants:   {', '.join(status['participants'])}")
        print(f"Local results:  {status['local_results']}")
        print(f"Global weight:  {status['global_weight']}")
