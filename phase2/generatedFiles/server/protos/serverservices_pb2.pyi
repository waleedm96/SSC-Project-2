from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class RegisterRequest(_message.Message):
    __slots__ = ("clientId", "name")
    CLIENTID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    clientId: str
    name: str
    def __init__(self, clientId: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class RegisterAnswer(_message.Message):
    __slots__ = ("answer", "message")
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    answer: bool
    message: str
    def __init__(self, answer: _Optional[bool] = ..., message: _Optional[str] = ...) -> None: ...
