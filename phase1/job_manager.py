"""
Step 4b - Job Manager.

Creates training jobs, stores them in a dictionary {job_id: TrainingJob}
and changes their status.
"""

from models import JobStatus, TrainingConfig, TrainingJob


class JobManager:
    def __init__(self):
        # 4.5 - The storage + a counter to build ids job-1, job-2, ...
        self._jobs: dict[str, TrainingJob] = {}
        self._next_id = 1

    # 4.6 - Create a new job (status CREATED)
    def create(self, config: TrainingConfig, participant_ids: list[str]) -> TrainingJob:
        if config.num_rounds < 1:
            raise ValueError("num_rounds must be at least 1")
        if not participant_ids:
            raise ValueError("A job needs at least one participant")

        job_id = f"job-{self._next_id}"
        self._next_id += 1
        job = TrainingJob(job_id=job_id, config=config,
                          participant_ids=list(participant_ids))
        self._jobs[job_id] = job
        return job

    # 4.7 - Get one job (error if unknown)
    def get(self, job_id: str) -> TrainingJob:
        if job_id not in self._jobs:
            raise KeyError(f"Unknown job '{job_id}'")
        return self._jobs[job_id]

    # 4.8 - Change the status and log the transition
    def update_status(self, job_id: str, status: JobStatus) -> None:
        job = self.get(job_id)
        print(f"[JobManager] {job_id}: {job.status.value} -> {status.value}")
        job.status = status
