"""Coordinator: main controller of the federated learning process."""

from models import TrainingConfig, TrainingJob, TrainingTask, TrainingResult, JobStatus
from participant import Participant
from registry import ParticipantRegistry
from job_manager import JobManager
from aggregator import Aggregator


class Coordinator:
    def __init__(self):
        # composition: the coordinator creates and owns these parts
        self._registry = ParticipantRegistry()
        self._job_manager = JobManager()
        self._aggregator = Aggregator()

    # ---------- public operations (used by the CLI) ----------

    def register_participant(self, name: str, data: list[float]) -> str:
        participant_id = f"p{len(self._registry.list_all()) + 1}"
        self._registry.add(Participant(participant_id, name, data))
        print(f"[Coordinator] registered {name} as {participant_id}")
        return participant_id

    def create_job(self, config: TrainingConfig) -> str:
        participant_ids = [p.participant_id for p in self._registry.list_all()]
        if not participant_ids:
            raise ValueError("Register at least one participant before creating a job")
        job = self._job_manager.create(config, participant_ids)
        print(f"[Coordinator] created {job.job_id} with participants {participant_ids}")
        return job.job_id

    def start_job(self, job_id: str) -> None:
        job = self._job_manager.get(job_id)
        if job.status != JobStatus.CREATED:
            raise ValueError(f"{job_id} cannot be started (status is {job.status.value})")

        self._job_manager.update_status(job_id, JobStatus.RUNNING)
        try:
            for round_number in range(1, job.config.num_rounds + 1):
                job.current_round = round_number
                print(f"[Coordinator] ---- {job_id} round {round_number} ----")

                task = self._distribute_task(job)
                results = self._collect_results(task)
                job.results.extend(results)
                job.global_weight = self._aggregator.aggregate(results)

            self._job_manager.update_status(job_id, JobStatus.COMPLETED)
            print(f"[Coordinator] {job_id} finished, global weight = {job.global_weight}")
        except Exception as error:
            self._job_manager.update_status(job_id, JobStatus.FAILED)
            print(f"[Coordinator] {job_id} failed: {error}")

    def get_status(self, job_id: str) -> TrainingJob:
        return self._job_manager.get(job_id)

    # ---------- private helpers ----------

    def _distribute_task(self, job: TrainingJob) -> TrainingTask:
        task = TrainingTask(
            job_id=job.job_id,
            round=job.current_round,
            global_weight=job.global_weight,
            config=job.config,
        )
        print(f"[Coordinator] sending task to {len(job.participant_ids)} participants "
              f"(global weight = {task.global_weight})")
        return task

    def _collect_results(self, task: TrainingTask) -> list[TrainingResult]:
        job = self._job_manager.get(task.job_id)
        results = []
        for participant_id in job.participant_ids:
            participant = self._registry.get(participant_id)
            results.append(participant.train(task))
        print(f"[Coordinator] received {len(results)} results")
        return results
