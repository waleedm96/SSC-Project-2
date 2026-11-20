"""Data classes of the monolithic FL application.

These match the green classes in the class diagram.
In Phase 2 each of them becomes a Protobuf message.
"""

from dataclasses import dataclass, field
from enum import Enum


class JobStatus(Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class TrainingConfig:
    num_rounds: int = 1
    initial_weight: float = 0.0


@dataclass
class TrainingTask:
    """What the coordinator sends to each participant."""
    job_id: str
    round: int
    global_weight: float
    config: TrainingConfig


@dataclass
class TrainingResult:
    """What a participant sends back after local training."""
    job_id: str
    participant_id: str
    round: int
    local_weight: float
    num_samples: int


@dataclass
class TrainingJob:
    """The state of one federated learning experiment."""
    job_id: str
    config: TrainingConfig
    participant_ids: list[str]
    status: JobStatus = JobStatus.CREATED
    current_round: int = 0
    global_weight: float = 0.0
    results: list[TrainingResult] = field(default_factory=list)
