"""
Step 4a - Participant Registry.

Stores the registered participants in a dictionary {participant_id: Participant}.
"""

from participant import Participant


class ParticipantRegistry:
    def __init__(self):
        # 4.1 - The storage: a dictionary for fast lookup by id
        self._participants: dict[str, Participant] = {}

    # 4.2 - Add a participant (reject duplicates)
    def add(self, participant: Participant) -> str:
        pid = participant.participant_id
        if pid in self._participants:
            raise ValueError(f"Participant '{pid}' is already registered")
        self._participants[pid] = participant
        return pid

    # 4.3 - Get one participant (error if unknown)
    def get(self, participant_id: str) -> Participant:
        if participant_id not in self._participants:
            raise KeyError(f"Unknown participant '{participant_id}'")
        return self._participants[participant_id]

    # 4.4 - All participants
    def list_all(self) -> list[Participant]:
        return list(self._participants.values())

    def __len__(self) -> int:
        return len(self._participants)
