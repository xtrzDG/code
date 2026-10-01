from enum import StrEnum


class PlanKey(StrEnum):
    """Subscription plan of one assistant ("employee")."""

    CHAT = "chat"
    VOICE_AND_CHAT = "voice_and_chat"
    PLUS = "plus"
