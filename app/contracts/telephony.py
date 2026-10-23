"""
Seams of the telephony line: the PBX that forwards calls to the assistant,
and the carrier's fallback when the voice platform cannot take a call.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.calls.call_fallback import (
    CallFallbackReply,
    CallFallbackReport,
    CallFallbackWebhookRequest,
)
from app.schemas.dto.calls.missed_calls import MissedCallReport, PbxCallWebhookRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber


class PbxWebhookAdapterContract(AdapterContract, Protocol):
    """Call notifications of the telephony line (Zadarma PBX)."""

    def verify_signature(self, request: PbxCallWebhookRequest) -> None:
        """
        Raise AuthenticationRequiredError unless the line signed the
        notification with the platform's API secret.
        """
        raise NotImplementedError

    def parse_missed_call(
        self,
        request: PbxCallWebhookRequest,
        now: Microseconds,
    ) -> MissedCallReport | None:
        """
        The caller who did not get through, from a verified notification
        about the end of an incoming call; None for other notifications
        and for calls that were answered (the voice platform reports
        those). Raises ValidationFailedError for a malformed notification.
        """
        raise NotImplementedError


class CallFallbackAdapterContract(AdapterContract, Protocol):
    """
    The carrier's call fallback (Twilio): it asks what to do with a call
    the voice platform could not take, then how the call to the staff
    mobile ended.
    """

    def read_fallback(
        self,
        request: CallFallbackWebhookRequest,
        now: Microseconds,
    ) -> CallFallbackReport:
        """
        The call of a fallback request. Raises AuthenticationRequiredError
        unless the carrier signed it for the business's address,
        ValidationFailedError when it names no call.
        """
        raise NotImplementedError

    def read_dial_outcome(
        self,
        request: CallFallbackWebhookRequest,
        now: Microseconds,
    ) -> MissedCallReport | None:
        """
        The caller who did not get through when the staff mobile was busy,
        rang out or failed (a missed call of the request's business); None
        when someone took the call. Raises like `read_fallback`.
        """
        raise NotImplementedError

    def transfer(
        self, business_id: BusinessId, phone_number: E164PhoneNumber
    ) -> CallFallbackReply:
        """
        Put the caller through to this number, reporting how it ended to
        the business's address.
        """
        raise NotImplementedError

    def end_call(self) -> CallFallbackReply:
        """Hang up."""
        raise NotImplementedError
