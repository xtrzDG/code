"""Reading the verifier's JSON answer back into a verdict per claim."""

import json
import re
from typing import cast

from app.schemas.constants.reply_safety import ClaimVerdict

JSON_OBJECT_PATTERN: re.Pattern[str] = re.compile(r"\{.*\}", re.DOTALL)


def read_verdicts(answer: str | None, claim_count: int) -> list[ClaimVerdict]:
    """
    A verdict for each of `claim_count` claims, in their order; a claim the
    answer does not judge readably (or an unreadable answer) is UNCHECKED.
    """

    verdicts: list[ClaimVerdict] = [ClaimVerdict.UNCHECKED] * claim_count
    for claim_id, is_supported in read_judgements(answer):
        if 1 <= claim_id <= claim_count:
            verdicts[claim_id - 1] = (
                ClaimVerdict.SUPPORTED if is_supported else ClaimVerdict.UNSUPPORTED
            )

    return verdicts


def read_judgements(answer: str | None) -> list[tuple[int, bool]]:
    """(claim id, supported) pairs of a readable answer; none otherwise."""

    if answer is None:
        return []

    match: re.Match[str] | None = JSON_OBJECT_PATTERN.search(answer)
    if match is None:
        return []

    try:
        payload: object = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, dict):
        return []

    verdicts: object = cast(dict[str, object], payload).get("verdicts")
    if not isinstance(verdicts, list):
        return []

    judgements: list[tuple[int, bool]] = []
    for verdict in cast(list[object], verdicts):
        if not isinstance(verdict, dict):
            continue

        fields: dict[str, object] = cast(dict[str, object], verdict)
        claim_id: object = fields.get("id")
        is_supported: object = fields.get("supported")
        if isinstance(claim_id, int) and isinstance(is_supported, bool):
            judgements.append((claim_id, is_supported))

    return judgements
