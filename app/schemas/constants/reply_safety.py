"""What the reply guard found in a reply and in a customer's message."""

from enum import StrEnum


class ClaimTopic(StrEnum):
    """
    The kind of statement the claim check verifies: a policy or a service
    term ("parking is free", "we take dogs", "free cancellation") or the
    availability of something ("we have a table", "delivery is available").
    """

    POLICY = "policy"
    AVAILABILITY = "availability"


class ClaimVerdict(StrEnum):
    """
    What the verifier said about one claim: the business's facts and tool
    results back it, they do not, or it could not be checked (the verifier
    failed or answered something unreadable; the reply is then sent).
    """

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNCHECKED = "unchecked"


class ReplyGuardReason(StrEnum):
    """
    Why the guard held back a reply (rewritten once or handed over): values
    the evidence does not back, policy or availability claims it does not
    back, or another person's phone number or e-mail address.
    """

    UNVERIFIED_VALUES = "unverified_values"
    UNSUPPORTED_CLAIMS = "unsupported_claims"
    PERSONAL_DATA = "personal_data"


class InjectionSignal(StrEnum):
    """
    The kind of prompt-injection attempt a customer message looks like:
    telling the assistant to drop its instructions, to become someone else,
    to reveal its instructions or other customers' data, or text faking the
    platform's own lines (system tags, fence keys, platform headers).
    """

    INSTRUCTION_OVERRIDE = "instruction_override"
    ROLE_CHANGE = "role_change"
    PROMPT_EXTRACTION = "prompt_extraction"
    DATA_EXFILTRATION = "data_exfiltration"
    FAKE_PLATFORM_TEXT = "fake_platform_text"
