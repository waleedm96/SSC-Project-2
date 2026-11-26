from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class JobStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    JOB_STATUS_UNSPECIFIED: _ClassVar[JobStatus]
    CREATED: _ClassVar[JobStatus]
    RUNNING: _ClassVar[JobStatus]
    COMPLETED: _ClassVar[JobStatus]
    FAILED: _ClassVar[JobStatus]
JOB_STATUS_UNSPECIFIED: JobStatus
CREATED: JobStatus
RUNNING: JobStatus
COMPLETED: JobStatus
FAILED: JobStatus

class TrainingConfig(_message.Message):
    __slots__ = ("num_rounds", "initial_weight")
    NUM_ROUNDS_FIELD_NUMBER: _ClassVar[int]
    INITIAL_WEIGHT_FIELD_NUMBER: _ClassVar[int]
    num_rounds: int
    initial_weight: float
    def __init__(self, num_rounds: _Optional[int] = ..., initial_weight: _Optional[float] = ...) -> None: ...

class TrainingTask(_message.Message):
    __slots__ = ("job_id", "round", "global_weight", "config")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    ROUND_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_WEIGHT_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    round: int
    global_weight: float
    config: TrainingConfig
    def __init__(self, job_id: _Optional[str] = ..., round: _Optional[int] = ..., global_weight: _Optional[float] = ..., config: _Optional[_Union[TrainingConfig, _Mapping]] = ...) -> None: ...

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

class TrainingJob(_message.Message):
    __slots__ = ("job_id", "config", "participant_ids", "status", "current_round", "global_weight", "results")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    PARTICIPANT_IDS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CURRENT_ROUND_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_WEIGHT_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    config: TrainingConfig
    participant_ids: _containers.RepeatedScalarFieldContainer[str]
    status: JobStatus
    current_round: int
    global_weight: float
    results: _containers.RepeatedCompositeFieldContainer[TrainingResult]
    def __init__(self, job_id: _Optional[str] = ..., config: _Optional[_Union[TrainingConfig, _Mapping]] = ..., participant_ids: _Optional[_Iterable[str]] = ..., status: _Optional[_Union[JobStatus, str]] = ..., current_round: _Optional[int] = ..., global_weight: _Optional[float] = ..., results: _Optional[_Iterable[_Union[TrainingResult, _Mapping]]] = ...) -> None: ...

class ParticipantInfo(_message.Message):
    __slots__ = ("participant_ip_addr", "name")
    PARTICIPANT_IP_ADDR_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    participant_ip_addr: str
    name: str
    def __init__(self, participant_ip_addr: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class RegisterParticipantRequest(_message.Message):
    __slots__ = ("participant_ip_addr", "name")
    PARTICIPANT_IP_ADDR_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    participant_ip_addr: str
    name: str
    def __init__(self, participant_ip_addr: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class RegisterParticipantReply(_message.Message):
    __slots__ = ("participant_ip_addr",)
    PARTICIPANT_IP_ADDR_FIELD_NUMBER: _ClassVar[int]
    participant_ip_addr: str
    def __init__(self, participant_ip_addr: _Optional[str] = ...) -> None: ...

class TrainingTaskRequest(_message.Message):
    __slots__ = ("task",)
    TASK_FIELD_NUMBER: _ClassVar[int]
    task: TrainingTask
    def __init__(self, task: _Optional[_Union[TrainingTask, _Mapping]] = ...) -> None: ...

class SubmitResultReply(_message.Message):
    __slots__ = ("accepted", "message")
    ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    accepted: bool
    message: str
    def __init__(self, accepted: _Optional[bool] = ..., message: _Optional[str] = ...) -> None: ...

class ListParticipantsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListParticipantsReply(_message.Message):
    __slots__ = ("participants",)
    PARTICIPANTS_FIELD_NUMBER: _ClassVar[int]
    participants: _containers.RepeatedCompositeFieldContainer[ParticipantInfo]
    def __init__(self, participants: _Optional[_Iterable[_Union[ParticipantInfo, _Mapping]]] = ...) -> None: ...

class CreateJobRequest(_message.Message):
    __slots__ = ("config",)
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    config: TrainingConfig
    def __init__(self, config: _Optional[_Union[TrainingConfig, _Mapping]] = ...) -> None: ...

class CreateJobReply(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class StartTrainingRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class StartTrainingReply(_message.Message):
    __slots__ = ("started", "message")
    STARTED_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    started: bool
    message: str
    def __init__(self, started: _Optional[bool] = ..., message: _Optional[str] = ...) -> None: ...

class TrainingStatusRequest(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...
