from enum import StrEnum


class VoiceCheckStatus(StrEnum):
    """
    How one simulated call of the voice checks ended at the voice platform:
    PASSED or FAILED by its evaluator; ERRORED when the platform could not
    run it (a refusal, a cancelled run, an outage); UNFINISHED when it was
    still running when the checks' time was up.
    """

    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"
    UNFINISHED = "unfinished"
