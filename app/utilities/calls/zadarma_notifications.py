"""
Notifications of the Zadarma PBX about incoming calls (form fields of a
POST to the notification address) and their signature.

Zadarma signs NOTIFY_START and NOTIFY_END with the account's API secret:
the `Signature` header is base64 of HMAC-SHA1 over caller_id + called_did
+ call_start (Zadarma's PHP example base64-encodes the hex digest; the raw
digest is accepted too).
"""

import base64
import hashlib
import hmac
from collections.abc import Mapping
from urllib.parse import parse_qs

from app.schemas.constants.calls import MissedCallReason

NOTIFY_END_EVENT: str = "NOTIFY_END"
SIGNED_EVENTS: frozenset[str] = frozenset({"NOTIFY_START", "NOTIFY_END"})
MAX_FORM_FIELDS: int = 64
# How an incoming call that the line did not put through ended. "answered"
# is missing on purpose: the voice platform reports those calls.
MISSED_DISPOSITIONS: Mapping[str, MissedCallReason] = {
    "busy": MissedCallReason.BUSY,
    "no answer": MissedCallReason.NO_ANSWER,
    "cancel": MissedCallReason.ABANDONED,
    "failed": MissedCallReason.LINE_FAILED,
    "no money": MissedCallReason.LINE_FAILED,
    "unallocated number": MissedCallReason.LINE_FAILED,
    "no limit": MissedCallReason.LINE_FAILED,
    "no day limit": MissedCallReason.LINE_FAILED,
    "line limit": MissedCallReason.LINE_FAILED,
    "no money, no limit": MissedCallReason.LINE_FAILED,
}


def read_form_fields(body: bytes) -> dict[str, str]:
    """The first value of every field of a form-encoded body."""

    try:
        text: str = body.decode("utf-8")
    except UnicodeDecodeError:
        return {}

    parsed: dict[str, list[str]] = parse_qs(
        text, keep_blank_values=True, max_num_fields=MAX_FORM_FIELDS
    )
    return {name: values[0] for name, values in parsed.items() if values}


def is_valid_zadarma_signature(
    api_secret: str,
    fields: Mapping[str, str],
    signature: str | None,
) -> bool:
    """The signature of a NOTIFY_START or NOTIFY_END notification."""

    if signature is None or fields.get("event") not in SIGNED_EVENTS:
        return False

    signed: bytes = (
        fields.get("caller_id", "")
        + fields.get("called_did", "")
        + fields.get("call_start", "")
    ).encode("utf-8")
    digest = hmac.new(api_secret.encode("utf-8"), signed, hashlib.sha1)
    expected: list[bytes] = [
        base64.b64encode(digest.hexdigest().encode("ascii")),
        base64.b64encode(digest.digest()),
    ]
    presented: bytes = signature.strip().encode("utf-8")
    return any(hmac.compare_digest(candidate, presented) for candidate in expected)


def read_missed_reason(disposition: str) -> MissedCallReason | None:
    """Why the caller did not get through; None for an answered call."""

    normalized: str = " ".join(disposition.replace("_", " ").lower().split())
    return MISSED_DISPOSITIONS.get(normalized)
