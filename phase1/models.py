"""
Step 1 - Data classes (no logic).

These classes only CARRY data between the components.
In Phase 2 they will become Protocol Buffers (gRPC) messages with the same fields.
"""

from dataclasses import dataclass, field
from enum import Enum


# 1.1 - The possible states of a training job
class JobStatus(Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# 1.2 - How the job should run (set by the Administrator)
@dataclass
class TrainingConfig:
    num_rounds: int = 1


# 1.3 - What the Coordinator sends TO each participant
@dataclass
class TrainingTask:
    job_id: str
    round_number: int
    global_weight: float


# 1.4 - What each participant sends BACK (only the result, never the data)
@dataclass
class TrainingResult:
    participant_id: str
    job_id: str
    round_number: int
    weight: float
    num_samples: int


# 1.5 - The job itself: config + who takes part + current state
@dataclass
class TrainingJob:
    job_id: str
    config: TrainingConfig
    participant_ids: list[str]
    status: JobStatus = JobStatus.CREATED
    global_weight: float = 0.0
    results: list[TrainingResult] = field(default_factory=list)
