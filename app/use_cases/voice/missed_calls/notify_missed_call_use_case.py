from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.call_follow_up_repositories import (
    CallSettingsRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.calls.call_summaries import CallReportTextInput, TextBackNote
from app.schemas.dto.calls.missed_calls import RegisteredMissedCall
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.use_cases.bookings.operations_support import display_phone
from app.use_cases.voice.summaries.call_report_alerts import (
    call_report_alert,
    call_report_texts,
)


class NotifyMissedCallUseCase(
    UseCaseContract[RegisteredMissedCall | None, DeliveredNotificationCount]
):
    """
    Tell staff about a caller who never reached the phone assistant (the
    line was busy or rang out, the caller hung up first, the assistant
    could not take the call): who called and when, why they did not get
    through and whether we wrote to them, on every channel, so someone
    calls back. Once per missed call; nothing while the owner keeps call
    summaries off. A call the assistant answered is reported by its
    summary instead.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        call_settings_repo: CallSettingsRepoContract,
        staff_alerts: StaffAlertFacilitatorContract,
        report_text_transformer: TransformerContract[CallReportTextInput, MessageText],
        report_brief_transformer: TransformerContract[
            CallReportTextInput, StaffAlertBrief
        ],
        phone_number_parser: PhoneNumberParserContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._call_settings_repo: CallSettingsRepoContract = call_settings_repo
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._report_text_transformer: TransformerContract[
            CallReportTextInput, MessageText
        ] = report_text_transformer
        self._report_brief_transformer: TransformerContract[
            CallReportTextInput, StaffAlertBrief
        ] = report_brief_transformer
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser

    def run(
        self, input_data: RegisteredMissedCall | None
    ) -> DeliveredNotificationCount:
        if input_data is None or not input_data.is_new:
            return DeliveredNotificationCount(0)

        missed: MissedCallDocument = input_data.missed_call
        business: BusinessDocument | None = self._business_repo.get(missed.business_id)
        settings: CallSettingsDocument | None = (
            None
            if business is None
            else self._call_settings_repo.get_by_business(business.id)
        )
        if business is None or (
            settings is not None and not settings.is_summary_enabled
        ):
            return DeliveredNotificationCount(0)

        facts = CallReportTextInput(
            business_name=business.name,
            language=business.owner_language,
            timezone=business.timezone,
            started_at=missed.called_at,
            caller_phone=display_phone(
                self._phone_number_parser, missed.caller_phone_number
            ),
            missed_reason=missed.reason,
            text_back=TextBackNote(
                status=missed.status,
                channel=missed.channel,
                skip_reason=missed.skip_reason,
            ),
        )
        return self._staff_alerts.alert(
            business,
            call_report_alert(
                business,
                StaffAlertSubject(f"missed_call:{missed.id}"),
                missed.conversation_id,
                None,
                is_missed=True,
            ),
            call_report_texts(
                facts,
                [],
                self._report_text_transformer,
                self._report_brief_transformer,
            ),
        )
