"""
Whether a business's campaign may write this hour, or is held for the
platform team's review over its opt-out rate (ABUSE-05).
"""

import logging
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.monitoring import SignalCounterAdapterContract
from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
    CampaignSettingsRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.campaigns import CampaignReviewHold, CampaignSettingsDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.campaigns.campaign_opt_out_review import (
    CampaignOptOutRate,
    measure_opt_outs,
)
from app.use_cases.shared.owner_contacts import owner_contacts
from app.utilities.campaigns.campaign_review_texts import (
    OWNER_HOLD_NOTICE,
    fill_hold_notice,
)

LOGGER: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CampaignReviewGate:
    """
    A held campaign stays held until a platform admin releases it. An
    unheld one is measured before it writes (after a release, only its
    messages sent since count): past the opt-out rate
    (`CampaignOptOutRate.needs_review`) it is held now, its owners are
    told why in their language, the platform signal `campaign_hold` counts
    once (the `campaign_opt_outs` alert) and a warning line names the
    business.
    """

    settings_repo: CampaignSettingsRepoContract
    message_repo: CampaignMessageRepoContract
    contact_repo: ContactRepoContract
    user_repo: UserRepoContract
    manager_notifier: ManagerNotificationFacilitatorContract
    text_resolver: LocalizedTextResolverContract
    signal_counter: SignalCounterAdapterContract | None

    def is_held(
        self,
        business: BusinessDocument,
        settings: CampaignSettingsDocument,
        now: Microseconds,
    ) -> bool:
        if settings.review_hold is not None:
            return True

        rate: CampaignOptOutRate = measure_opt_outs(
            self.message_repo,
            self.contact_repo,
            business.id,
            now,
            settings.review_released_at,
        )
        if not rate.needs_review():
            return False

        hold: CampaignReviewHold = rate.hold(now)
        # Read again just before the write: an owner's save made while the
        # messages were counted is kept.
        latest: CampaignSettingsDocument = (
            self.settings_repo.get_by_business(business.id) or settings
        )
        self.settings_repo.save(latest.model_copy(update={"review_hold": hold}))
        LOGGER.warning(
            "The campaign of %s is held for review: %d of %d customers opted out.",
            business.id,
            int(hold.opted_out),
            int(hold.sent),
        )
        if self.signal_counter is not None:
            self.signal_counter.count(PlatformSignal.CAMPAIGN_HOLD)

        for owner in owner_contacts(business, self.user_repo):
            self.manager_notifier.notify(
                StaffNotification(
                    business_id=business.id,
                    contact=owner,
                    text=MessageText(
                        fill_hold_notice(
                            str(
                                self.text_resolver.resolve(
                                    OWNER_HOLD_NOTICE, owner.language
                                )
                            ),
                            str(business.name),
                            hold,
                        )
                    ),
                )
            )

        return True
