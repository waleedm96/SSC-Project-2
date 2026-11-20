"""
Step 5 - Coordinator (the main controller, "server" in Flower terms).

It OWNS (composition) the registry, the job manager and the aggregator,
and runs the Federated Learning rounds:

    distribute task -> participants train locally -> collect results -> aggregate

In Phase 2 this class becomes the Coordinator Service (gRPC server).
"""

from aggregator import Aggregator
from job_manager import JobManager
from models import JobStatus, TrainingConfig, TrainingResult, TrainingTask, TrainingJob
from participant import Participant
from registry import ParticipantRegistry


class Coordinator:
    # 5.1 - Composition: the coordinator creates and owns its components
    def __init__(self):
        self._registry = ParticipantRegistry()
        self._job_manager = JobManager()
        self._aggregator = Aggregator()
        self._next_participant = 1

    # ---------------------------------------------------------------- public

    # 5.2 - Register a participant -> returns its id (p1, p2, ...)
    def register_participant(self, name: str, data: list[float]) -> str:
        if any(p.name == name for p in self._registry.list_all()):
            raise ValueError(f"A participant named '{name}' is already registered")
        pid = f"p{self._next_participant}"
        self._registry.add(Participant(pid, name, data))
        self._next_participant += 1
        print(f"[Coordinator] registered {name} as {pid}")
        return pid

    # 5.3 - Create a job with all registered participants -> returns job id
    def create_job(self, config: TrainingConfig) -> str:
        participant_ids = [p.participant_id for p in self._registry.list_all()]
        job = self._job_manager.create(config, participant_ids)
        print(f"[Coordinator] created {job.job_id} with participants {participant_ids}")
        return job.job_id

    # 5.4 - Run the job: the full FL workflow
    def start_job(self, job_id: str) -> float:
        job = self._job_manager.get(job_id)
        if job.status != JobStatus.CREATED:
            raise ValueError(f"{job_id} is {job.status.value}, it can only start when CREATED")

        self._job_manager.update_status(job_id, JobStatus.RUNNING)
        try:
            for round_number in range(1, job.config.num_rounds + 1):
                print(f"[Coordinator] ---- {job_id} round {round_number} ----")
                task = self._distribute_task(job, round_number)
                results = self._collect_results(job, task)

                # every participant must answer, otherwise the round fails
                if len(results) != len(job.participant_ids):
                    raise RuntimeError(
                        f"expected {len(job.participant_ids)} results, got {len(results)}")

                job.results.extend(results)
                job.global_weight = self._aggregator.aggregate(results)

            self._job_manager.update_status(job_id, JobStatus.COMPLETED)
            print(f"[Coordinator] {job_id} finished, global weight = {job.global_weight}")
            return job.global_weight

        except Exception as error:
            print(f"[Coordinator] {job_id} failed: {error}")
            self._job_manager.update_status(job_id, JobStatus.FAILED)
            raise

    # 5.5 - What the Administrator sees
    def get_status(self, job_id: str) -> dict:
        job = self._job_manager.get(job_id)
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "rounds": job.config.num_rounds,
            "participants": job.participant_ids,
            "local_results": {r.participant_id: r.weight for r in job.results},
            "global_weight": job.global_weight,
        }

    # --------------------------------------------------------------- private

    # 5.6 - Build the task that is sent to every participant
    def _distribute_task(self, job: TrainingJob, round_number: int) -> TrainingTask:
        print(f"[Coordinator] sending task to {len(job.participant_ids)} participants "
              f"(global weight = {job.global_weight})")
        return TrainingTask(job_id=job.job_id, round_number=round_number,
                            global_weight=job.global_weight)

    # 5.7 - Ask each participant to train and collect only their results
    def _collect_results(self, job: TrainingJob, task: TrainingTask) -> list[TrainingResult]:
        results = []
        for pid in job.participant_ids:
            participant = self._registry.get(pid)
            results.append(participant.train(task))
        print(f"[Coordinator] received {len(results)} results")
        return results
