"""
Step 2 - Participant.

A participant owns PRIVATE local data. It trains on that data and returns
only a TrainingResult (weight + number of samples), never the data itself.
In Phase 2 each participant will be its own process (gRPC client).
"""

from models import TrainingTask, TrainingResult


class Participant:
    # 2.1 - Constructor: id, name and private data
    def __init__(self, participant_id: str, name: str, data: list[float]):
        if not data:
            raise ValueError("A participant needs at least one data value")
        self.participant_id = participant_id
        self.name = name
        self._data = list(data)  # "_" = private: other classes must not read it

    # 2.2 - Read-only information about the data (not the data itself)
    @property
    def num_samples(self) -> int:
        return len(self._data)

    # 2.3 - Local training (simulated): the mean of the local data
    def train(self, task: TrainingTask) -> TrainingResult:
        local_weight = sum(self._data) / self.num_samples
        print(f"[{self.name}] training on {self.num_samples} samples "
              f"-> local weight = {local_weight}")

        # 2.4 - Send back ONLY the result
        return TrainingResult(
            participant_id=self.participant_id,
            job_id=task.job_id,
            round_number=task.round_number,
            weight=local_weight,
            num_samples=self.num_samples,
        )
