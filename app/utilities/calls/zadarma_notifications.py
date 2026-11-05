"""
Notifications of the Zadarma PBX about incoming calls (form fields of a
POST to the notification address) and their signature.

Zadarma signs NOTIFY_START and NOTIFY_END with the account's API secret:
the `Signature` header is base64 of HMAC-SHA1 over caller_id + called_did
+ call_start (Zadarma's PHP example base64-encodes the hex digest; the raw
digest is accepted too).

The signature has no timestamp of its own and leaves the call id out, so
replays are judged by what it covers: `call_start` ("YYYY-MM-DD HH:MM:SS"
in the PBX account's time zone, whatever its UTC offset) must be recent,
and the signed fields are claimed once (`signed_content_digest`).
"""

import base64
import hashlib
import hmac
from collections.abc import Mapping
from datetime import UTC, datetime
from urllib.parse import parse_qs

from app.schemas.constants.calls import MissedCallReason

NOTIFY_END_EVENT: str = "NOTIFY_END"
SIGNED_EVENTS: frozenset[str] = frozenset({"NOTIFY_START", "NOTIFY_END"})
MAX_FORM_FIELDS: int = 64
CALL_START_FORMAT: str = "%Y-%m-%d %H:%M:%S"
HOUR_SECONDS: int = 60 * 60
# `call_start` is the PBX's local time, read here as if it were UTC: a zone
# up to 14 h east makes it look that much ahead of the platform's clock
# (and a few minutes of clock skew on top).
CALL_START_LEAD_SECONDS: int = 14 * HOUR_SECONDS + 5 * 60
# How old it may look: a zone up to 12 h west and the call itself. A
# notification is sent when the call ends, so a real one is never older;
# older ones are replays (and their claims, kept for a day after
# `call_start`, are gone by then).
CALL_START_MAX_AGE_SECONDS: int = 24 * HOUR_SECONDS
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


def read_call_start_seconds(fields: Mapping[str, str]) -> int | None:
    """`call_start` as Unix seconds, read as UTC; None when unreadable."""

    try:
        moment: datetime = datetime.strptime(
            fields.get("call_start", "").strip(), CALL_START_FORMAT
        )
    except ValueError:
        return None

    return int(moment.replace(tzinfo=UTC).timestamp())


def is_recent_call_start(call_start_seconds: int, now_seconds: int) -> bool:
    """Whether a signed `call_start` can belong to a call of now."""

    age: int = now_seconds - call_start_seconds
    return -CALL_START_LEAD_SECONDS <= age <= CALL_START_MAX_AGE_SECONDS


def signed_content_digest(fields: Mapping[str, str]) -> str:
    """
    SHA-256 of what the signature covers, with the event: the same for a
    repeat of one notification and for a copy with another call id.
    """

    signed: str = "\x00".join(
        fields.get(name, "")
        for name in ("event", "caller_id", "called_did", "call_start")
    )
    return hashlib.sha256(signed.encode("utf-8")).hexdigest()


def call_id_digest(fields: Mapping[str, str]) -> str:
    """SHA-256 of the (unsigned) call id of a notification."""

    return hashlib.sha256(
        fields.get("pbx_call_id", "").strip().encode("utf-8")
    ).hexdigest()


def read_missed_reason(disposition: str) -> MissedCallReason | None:
    """Why the caller did not get through; None for an answered call."""

    normalized: str = " ".join(disposition.replace("_", " ").lower().split())
    return MISSED_DISPOSITIONS.get(normalized)
