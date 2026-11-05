"""
Zero-downtime rotation of webhook secrets: a verifier accepts the current
value, then the previous one (`<NAME>_PREVIOUS`) while the provider still
signs with it. Only verification reads the previous value; requests the
platform signs always use the current one.
"""

from app.schemas.typings.platform.strings import PlatformSecret


def accepted_secrets(
    current: PlatformSecret | None,
    previous: PlatformSecret | None,
) -> list[PlatformSecret]:
    """
    The values a signature may be checked against, the current one first.
    None without a current value: a previous value alone never opens
    anything (the feature is off).
    """

    if current is None:
        return []

    if previous is None or str(previous) == str(current):
        return [current]

    return [current, previous]
