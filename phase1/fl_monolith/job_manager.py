"""JobManager: creates training jobs and tracks their status."""

from models import TrainingConfig, TrainingJob, JobStatus


class JobManager:
    def __init__(self):
        self._jobs: dict[str, TrainingJob] = {}

    def create(self, config: TrainingConfig, participant_ids: list[str]) -> TrainingJob:
        job_id = f"job-{len(self._jobs) + 1}"
        job = TrainingJob(
            job_id=job_id,
            config=config,
            participant_ids=participant_ids,
            global_weight=config.initial_weight,
        )
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> TrainingJob:
        if job_id not in self._jobs:
            raise KeyError(f"Unknown job: {job_id}")
        return self._jobs[job_id]

    def update_status(self, job_id: str, status: JobStatus) -> None:
        job = self.get(job_id)
        print(f"  [JobManager] {job_id}: {job.status.value} -> {status.value}")
        job.status = status
