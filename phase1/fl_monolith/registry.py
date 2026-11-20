"""ParticipantRegistry: keeps the list of registered participants."""

from participant import Participant


class ParticipantRegistry:
    def __init__(self):
        self._participants: dict[str, Participant] = {}

    def add(self, participant: Participant) -> str:
        if participant.participant_id in self._participants:
            raise ValueError(f"Participant {participant.participant_id} is already registered")
        self._participants[participant.participant_id] = participant
        return participant.participant_id

    def get(self, participant_id: str) -> Participant:
        if participant_id not in self._participants:
            raise KeyError(f"Unknown participant: {participant_id}")
        return self._participants[participant_id]

    def list_all(self) -> list[Participant]:
        return list(self._participants.values())
