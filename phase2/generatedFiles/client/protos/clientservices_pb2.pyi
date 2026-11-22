from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class TrainingTask(_message.Message):
    __slots__ = ("job_id", "round", "global_weight", "num_rounds", "initial_weight")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    ROUND_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_WEIGHT_FIELD_NUMBER: _ClassVar[int]
    NUM_ROUNDS_FIELD_NUMBER: _ClassVar[int]
    INITIAL_WEIGHT_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    round: int
    global_weight: float
    num_rounds: int
    initial_weight: float
    def __init__(self, job_id: _Optional[str] = ..., round: _Optional[int] = ..., global_weight: _Optional[float] = ..., num_rounds: _Optional[int] = ..., initial_weight: _Optional[float] = ...) -> None: ...

class TrainingResult(_message.Message):
    __slots__ = ("job_id", "participant_id", "round", "local_weight", "num_samples")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    PARTICIPANT_ID_FIELD_NUMBER: _ClassVar[int]
    ROUND_FIELD_NUMBER: _ClassVar[int]
    LOCAL_WEIGHT_FIELD_NUMBER: _ClassVar[int]
    NUM_SAMPLES_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    participant_id: str
    round: int
    local_weight: float
    num_samples: int
    def __init__(self, job_id: _Optional[str] = ..., participant_id: _Optional[str] = ..., round: _Optional[int] = ..., local_weight: _Optional[float] = ..., num_samples: _Optional[int] = ...) -> None: ...
