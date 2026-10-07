from app.schemas.exceptions.application_errors import ExternalServiceError


class LlmCassetteMissError(ExternalServiceError):
    """
    A replayed model call has no recording (the instruction, the tools or
    the conversation changed since the cassette was recorded). The engine
    treats it like an unavailable provider; the replay adapter keeps the
    reason so the evaluation harness can flag the cassette.
    """
