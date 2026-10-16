"""Seams of the telephony line (the PBX that forwards calls to the assistant)."""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.calls.missed_calls import MissedCallReport, PbxCallWebhookRequest


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
