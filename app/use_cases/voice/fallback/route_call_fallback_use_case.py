import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
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
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.use_cases.voice.call_admission import is_blocked_caller
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
    first manager reachable by phone). The staff phone sees the line that
    was called (the platform's rented number) as the caller id, never the
    caller's own number.

    With nobody to put the call through to (no such phone, or the call
    comes from that very phone, was forwarded from it or that phone is the
    line itself, which would ring in a loop), or no line to present, the
    call ends and is a missed call of the line (NOT_STARTED) with its
    text-back. A call from the line itself, with a staff phone on duty, is
    the call put through to that phone coming back: the phone forwarded it
    to the line, and not every carrier says so (Twilio's ForwardedFrom).
    It is rejected unanswered, as busy, and is no missed call (no person
    presents the platform's own line): the phone's forwarding fails, so
    the caller's own call to it ends unanswered and is their missed call
    (`ReadFallbackDialUseCase`). Answering it, even to hang up, would
    complete the call put through and lose the caller, so this comes
    before the blocked check: a contact holding the line's own number
    (say, a spoofed call staff blocked) is no person. A business that is
    gone: the call ends. So does a call from a number staff blocked
    (`is_blocked_caller`), which the voice agent refused: it reaches
    nobody and is no missed call. A signed copy of a request already
    handled (Twilio's signature has no time) changes nothing: no phone
    rings, no missed call, no notice.
    """

    def __init__(
        self,
        call_fallback_adapter: CallFallbackAdapterContract,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        contact_repo: ContactRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._call_fallback_adapter: CallFallbackAdapterContract = call_fallback_adapter
        self._contact_repo: ContactRepoContract = contact_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CallFallbackWebhookRequest) -> CallFallbackPlan:
        now: Microseconds = self._wall_clock.now_unix()
        report: CallFallbackReport = self._call_fallback_adapter.read_fallback(
            input_data, now
        )
        if report.is_repeated:
            logger.warning(
                "Fallback call %s was asked about again (a signed copy); ignored.",
                report.provider_call_id,
            )
            return CallFallbackPlan(
                reply=self._call_fallback_adapter.ignore_request(),
                called_at=now,
                business_id=input_data.business_id,
                is_repeated=True,
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

        caller: E164PhoneNumber | None = self._parse(business, report.caller_number)
        transfer: E164PhoneNumber | None = find_transfer_phone_number(
            business, self._business_profile_repo.get_by_business(business.id)
        )
        # The staff phone sees the platform's line, never the caller's number.
        line: E164PhoneNumber | None = self._parse(business, report.assistant_number)
        # Before the blocked check: a block on a contact holding the line's
        # number (a spoofed call staff blocked) is about no person, and ending
        # the call would answer it and lose the caller put through.
        if transfer is not None and _is_same_number(caller, line):
            logger.info(
                "Fallback call %s comes from the line itself (the staff phone "
                "forwarded it back); it was rejected.",
                report.provider_call_id,
            )
            return CallFallbackPlan(
                reply=self._call_fallback_adapter.reject_call(),
                called_at=now,
                business_id=business.id,
                looping_phone_number=transfer,
            )

        if is_blocked_caller(self._contact_repo, business, caller):
            logger.info(
                "Fallback call %s comes from a blocked number; it was ended.",
                report.provider_call_id,
            )
            return CallFallbackPlan(
                reply=self._call_fallback_adapter.end_call(),
                called_at=now,
                business_id=business.id,
                is_caller_blocked=True,
            )

        is_loop: bool = transfer is not None and self._loops_back(
            business, report, transfer, caller, line
        )
        if transfer is not None and not is_loop and line is not None:
            return CallFallbackPlan(
                reply=self._call_fallback_adapter.transfer(business.id, transfer, line),
                called_at=now,
                business_id=business.id,
                transfer_phone_number=transfer,
            )

        return CallFallbackPlan(
            reply=self._call_fallback_adapter.end_call(),
            called_at=now,
            business_id=business.id,
            looping_phone_number=transfer if is_loop else None,
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
        caller: E164PhoneNumber | None,
        line: E164PhoneNumber | None,
    ) -> bool:
        """
        Whether the call comes from the staff mobile, was forwarded by it, or
        the staff mobile is the line that was called (dialing it would fail
        into this fallback again).
        """

        forwarded_from: E164PhoneNumber | None = self._parse(
            business, report.forwarded_from
        )
        return any(
            _is_same_number(number, transfer)
            for number in (caller, forwarded_from, line)
        )

    def _parse(
        self, business: BusinessDocument, raw_number: RawPhoneNumberInput | None
    ) -> E164PhoneNumber | None:
        """A number the carrier reported, read with the business country as hint."""

        if raw_number is None:
            return None

        return parse_messaging_phone_number(
            self._phone_number_parser, str(raw_number), business.country_code
        )


def _is_same_number(
    number: E164PhoneNumber | None, other: E164PhoneNumber | None
) -> bool:
    """Whether both numbers are known and are the same line."""

    return number is not None and other is not None and str(number) == str(other)
