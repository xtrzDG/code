"""
Telling the team a milestone happened (the push of a milestone's
celebration): every device of the team and the Telegram chats linked to
the platform bot hear it once, with a link to the Overview, where the
cabinet shows the celebration. Milestones noticed long after they happened
(data from before milestones were celebrated) are not announced.
"""

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.notifications.staff_alerts import StaffAlert, StaffAlertBrief
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import (
    PushNotificationTag,
    StaffAlertSubject,
)
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.use_cases.shared.staff_alerts import StaffAlertTexts
from app.utilities.setup.milestone_texts import (
    CELEBRATED_MILESTONES,
    MILESTONE_DETAILS,
    MILESTONE_TITLES,
)

# A milestone older than this is old news: the cabinet still shows it once,
# but nobody's phone buzzes for it.
ANNOUNCE_WITHIN_MICROSECONDS: int = 24 * 60 * 60 * 1_000_000


def announce_milestone(
    staff_alerts: StaffAlertFacilitatorContract,
    resolver: LocalizedTextResolverContract,
    business: BusinessDocument,
    kind: ActivationEventKind,
    occurred_at: Microseconds,
    now: Microseconds,
) -> None:
    """Push a celebrated milestone that just happened; never raises."""

    if kind not in CELEBRATED_MILESTONES or (
        int(now) - int(occurred_at) > ANNOUNCE_WITHIN_MICROSECONDS
    ):
        return

    def brief(language: LanguageTag) -> StaffAlertBrief:
        return StaffAlertBrief(
            title=StaffAlertTitle(resolver.resolve(MILESTONE_TITLES[kind], language)),
            detail=StaffAlertDetail(
                resolver.resolve(MILESTONE_DETAILS[kind], language).replace(
                    "{name}", str(business.name)
                )
            ),
        )

    def detailed(language: LanguageTag) -> MessageText:
        lines: StaffAlertBrief = brief(language)
        return MessageText(f"{lines.title}\n{lines.detail}")

    staff_alerts.alert(
        business,
        StaffAlert(
            business_id=business.id,
            target=StaffLinkTarget.OVERVIEW,
            tag=PushNotificationTag(f"milestone:{kind.value}"),
            subject=StaffAlertSubject(f"milestone:{kind.value}"),
            contact_channels=[ManagerContactChannel.TELEGRAM],
        ),
        StaffAlertTexts(detailed=detailed, brief=brief),
    )
