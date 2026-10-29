"""Bookings → Return visits: the campaign's settings as the owner sees them."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from typed_time_provider import Microseconds

from app.contracts.growth import RebookingRuleRegistryContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
)
from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.campaigns import CampaignSettingsDocument
from app.schemas.dto.growth.campaign_views import (
    CampaignMessagePreview,
    CampaignSettingsView,
)
from app.schemas.dto.growth.rebooking_rules import RebookingRule
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.campaigns.campaign_keys import (
    campaign_month_of,
    campaign_settings_id_of,
)
from app.utilities.campaigns.campaign_texts import CAMPAIGN_TEXTS
from app.utilities.scheduling.localized_formatting import format_full_date
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * MICROSECONDS_PER_SECOND
# The counts by status cover the last 30 days.
RECENT_DAYS: int = 30


def stored_or_niche_default(
    settings: CampaignSettingsDocument | None,
    business: BusinessDocument,
    rule: RebookingRule,
    now: Microseconds,
) -> CampaignSettingsDocument:
    """The stored settings, else the niche's rule, off until the owner opts in."""

    if settings is not None:
        return settings

    return CampaignSettingsDocument(
        id=campaign_settings_id_of(business.id),
        business_id=business.id,
        rule_kind=rule.rule_kind,
        delay_days=rule.delay_days,
        created_at=now,
        updated_at=now,
    )


@dataclass(frozen=True)
class CampaignSettingsReader:
    """Builds the settings view: the niche's rule, the month, previews."""

    message_repo: CampaignMessageRepoContract
    segment_repo: CustomerSegmentRepoContract
    rule_registry: RebookingRuleRegistryContract
    text_resolver: LocalizedTextResolverContract

    def niche_rule(self, business: BusinessDocument) -> RebookingRule:
        return self.rule_registry.get(business.niche_key)

    def view(
        self,
        business: BusinessDocument,
        settings: CampaignSettingsDocument,
        now: Microseconds,
    ) -> CampaignSettingsView:
        rule: RebookingRule = self.niche_rule(business)
        zone = load_time_zone(business.timezone)
        segment = (
            None
            if settings.segment_id is None
            else self.segment_repo.get(business.id, settings.segment_id)
        )
        return CampaignSettingsView(
            is_enabled=settings.is_enabled,
            rule_kind=settings.rule_kind,
            delay_days=settings.delay_days,
            audience=settings.audience,
            segment_id=settings.segment_id,
            segment_name=None if segment is None else segment.name,
            monthly_cap=settings.monthly_cap,
            niche_rule_kind=rule.rule_kind,
            niche_delay_days=rule.delay_days,
            month_sent_count=self.message_repo.count_sent_in_month(
                business.id, campaign_month_of(now, zone)
            ),
            recent_counts=self.message_repo.count_by_status(
                business.id,
                Microseconds(int(now) - RECENT_DAYS * MICROSECONDS_PER_DAY),
            ),
            previews=[
                self._preview(business, settings, language, now)
                for language in business.languages
            ],
        )

    def _preview(
        self,
        business: BusinessDocument,
        settings: CampaignSettingsDocument,
        language: LanguageTag,
        now: Microseconds,
    ) -> CampaignMessagePreview:
        """The message as a customer would read it, an arrival in `delay_days`."""

        zone = load_time_zone(business.timezone)
        arrival: datetime = datetime.fromtimestamp(
            int(now) / MICROSECONDS_PER_SECOND, zone
        ) + timedelta(days=int(settings.delay_days))
        template: str = str(
            self.text_resolver.resolve(CAMPAIGN_TEXTS[settings.rule_kind], language)
        )
        return CampaignMessagePreview(
            language=language,
            text=MessageText(
                template.format(
                    business=str(business.name),
                    date=format_full_date(arrival.date(), language),
                )
            ),
        )
