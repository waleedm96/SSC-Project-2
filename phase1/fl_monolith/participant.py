"""Participant: keeps its data locally and trains on it."""

from models import TrainingTask, TrainingResult


class Participant:
    def __init__(self, participant_id: str, name: str, local_data: list[float]):
        self._participant_id = participant_id
        self._name = name
        self._local_data = local_data      # private: never sent to the coordinator

    @property
    def participant_id(self) -> str:
        return self._participant_id

    @property
    def name(self) -> str:
        return self._name

    def num_samples(self) -> int:
        return len(self._local_data)

    def train(self, task: TrainingTask) -> TrainingResult:
        """Simulated local training: the local model is the mean of the local data."""
        local_weight = sum(self._local_data) / len(self._local_data)

        print(f"  [{self._name}] training on {self.num_samples()} samples "
              f"-> local weight = {local_weight}")

        # only the result leaves the participant, not the data
        return TrainingResult(
            job_id=task.job_id,
            participant_id=self._participant_id,
            round=task.round,
            local_weight=local_weight,
            num_samples=self.num_samples(),
        )
