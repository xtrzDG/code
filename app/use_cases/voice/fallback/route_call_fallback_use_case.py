import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.telephony import CallFallbackAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.calls import MissedCallReason, MissedCallSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.calls.call_fallback import (
    CallFallbackPlan,
    CallFallbackReport,
    CallFallbackWebhookRequest,
)
from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.channels.channel_phone_numbers import parse_messaging_phone_number
from app.utilities.channels.voice_service import find_transfer_phone_number

logger: logging.Logger = logging.getLogger(__name__)


class RouteCallFallbackUseCase(
    UseCaseContract[CallFallbackWebhookRequest, CallFallbackPlan]
):
    """
    Answer the carrier's fallback for a call to a business's rented number
    the voice platform could not take (it refused the call, or did not
    answer in time): check the carrier's signature on the business's
    address, then put the caller through to the staff mobile on duty, the
    number the agent transfers to (the profile's handoff phone, else the
    first manager reachable by phone).

    With nobody to put the call through to (no such phone, or the call
    comes from that very phone or was forwarded from it, which would ring
    in a loop) the call ends and is a missed call of the line (NOT_STARTED)
    with its text-back. A business that is gone: the call ends.
    """

    def __init__(
        self,
        call_fallback_adapter: CallFallbackAdapterContract,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._call_fallback_adapter: CallFallbackAdapterContract = call_fallback_adapter
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CallFallbackWebhookRequest) -> CallFallbackPlan:
        now: Microseconds = self._wall_clock.now_unix()
        report: CallFallbackReport = self._call_fallback_adapter.read_fallback(
            input_data, now
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            logger.warning(
                "Fallback call %s reached business %s, which is gone; it was ended.",
                report.provider_call_id,
                input_data.business_id,
            )
            return CallFallbackPlan(
                reply=self._call_fallback_adapter.end_call(),
                called_at=now,
                business_id=input_data.business_id,
            )

        transfer: E164PhoneNumber | None = find_transfer_phone_number(
            business, self._business_profile_repo.get_by_business(business.id)
        )
        if transfer is not None and not self._loops_back(business, report, transfer):
            return CallFallbackPlan(
                reply=self._call_fallback_adapter.transfer(business.id, transfer),
                called_at=now,
                business_id=business.id,
                transfer_phone_number=transfer,
            )

        return CallFallbackPlan(
            reply=self._call_fallback_adapter.end_call(),
            called_at=now,
            business_id=business.id,
            missed_call=MissedCallReport(
                source=MissedCallSource.PBX,
                provider_call_id=report.provider_call_id,
                reason=MissedCallReason.NOT_STARTED,
                called_at=now,
                business_id=business.id,
                assistant_number=report.assistant_number,
                caller_number=report.caller_number,
            ),
        )

    def _loops_back(
        self,
        business: BusinessDocument,
        report: CallFallbackReport,
        transfer: E164PhoneNumber,
    ) -> bool:
        """Whether the call comes from the staff mobile or was forwarded by it."""

        for raw_number in (report.caller_number, report.forwarded_from):
            number: E164PhoneNumber | None = (
                None
                if raw_number is None
                else parse_messaging_phone_number(
                    self._phone_number_parser, str(raw_number), business.country_code
                )
            )
            if number is not None and str(number) == str(transfer):
                return True

        return False
