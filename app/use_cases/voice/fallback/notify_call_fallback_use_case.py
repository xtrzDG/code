from app.contracts.localization_utilities import (
    LocalizedTextResolverContract,
    PhoneNumberParserContract,
)
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.calls.call_fallback import CallFallbackPlan
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.notifications.constrained_strings import (
    PushNotificationTag,
    StaffAlertSubject,
)
from app.use_cases.shared.operations_support import display_phone
from app.utilities.calls.voice_fallback_texts import VoiceFallbackTexts

MICROSECONDS_PER_HOUR: int = 3600 * 1_000_000


class NotifyCallFallbackUseCase(
    UseCaseContract[CallFallbackPlan, DeliveredNotificationCount]
):
    """
    Tell the owner that the phone assistant could not take a call and the
    line's fallback took over: the call was put through to the staff
    mobile (which number), or with nobody to take it, it is a missed call
    (add a phone for calls that need a person). Queued in the outbox of
    staff alerts for the owners' devices and the staff contacts (a link to
    Channels), at most once an hour per business: while the voice platform
    is down every call falls back, and one notice says it.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        staff_alerts: StaffAlertFacilitatorContract,
        text_resolver: LocalizedTextResolverContract,
        phone_number_parser: PhoneNumberParserContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser

    def run(self, input_data: CallFallbackPlan) -> DeliveredNotificationCount:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            return DeliveredNotificationCount(0)

        hour: int = int(input_data.called_at) // MICROSECONDS_PER_HOUR
        return self._staff_alerts.alert(
            business,
            StaffAlert(
                business_id=business.id,
                target=StaffLinkTarget.CHANNELS,
                tag=PushNotificationTag(f"voice_fallback:{business.id}"),
                subject=StaffAlertSubject(f"voice_fallback:{business.id}-{hour}"),
                member_roles=[BusinessMemberRole.OWNER],
            ),
            VoiceFallbackTexts(
                self._text_resolver,
                business.name,
                display_phone(
                    self._phone_number_parser, input_data.transfer_phone_number
                ),
                display_phone(
                    self._phone_number_parser, input_data.looping_phone_number
                ),
            ),
        )
