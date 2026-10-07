"""What contact and device tests share: their limit, link and text."""

from typed_time_provider import Microseconds

from app.contracts.notification_utilities import StaffLinkSignerContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.notifications.staff_alerts import (
    StaffAlertBrief,
    StaffAlertBriefInput,
)
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.deliveries.constrained_strings import OutboundRecipientKey
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import CabinetDeepLink
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.utilities.notifications.cabinet_links import build_cabinet_link, link_expiry
from app.utilities.notifications.staff_delivery_keys import test_rate_limit_key

# Tests one recipient may get per hour (an SMS costs money each time).
TESTS_PER_HOUR: RequestsPerWindow = RequestsPerWindow(5)
TEST_WINDOW_SECONDS: RateWindowSeconds = RateWindowSeconds(60 * 60)


def check_test_budget(
    rate_limits: RequestRateLimitRegistryContract,
    business: BusinessDocument,
    recipient_key: OutboundRecipientKey,
    now: Microseconds,
) -> None:
    """RateLimitedError (with Retry-After) after 5 tests within an hour."""

    counter = RateLimitCounter(
        key=test_rate_limit_key(business.id, recipient_key), limit=TESTS_PER_HOUR
    )
    if rate_limits.try_acquire_all([counter], TEST_WINDOW_SECONDS, now) is None:
        return

    raise RateLimitedError(
        "Too many test notifications to this recipient; try again later.",
        retry_after_seconds=rate_limits.seconds_until_free(
            counter, TEST_WINDOW_SECONDS, now
        ),
    )


def settings_link(
    signer: StaffLinkSignerContract,
    settings: AppSettings,
    business: BusinessDocument,
    now: Microseconds,
) -> CabinetDeepLink | None:
    """A test opens the notification settings."""

    return build_cabinet_link(
        signer,
        settings.cabinet_base_url,
        StaffLinkClaims(
            business_id=business.id,
            target=StaffLinkTarget.NOTIFICATIONS,
            expires_at=link_expiry(now),
        ),
    )


def check_brief(
    brief_transformer: TransformerContract[StaffAlertBriefInput, StaffAlertBrief],
    business: BusinessDocument,
    language: LanguageTag,
) -> StaffAlertBrief:
    return brief_transformer.transform(
        StaffAlertBriefInput(business_name=business.name, language=language)
    )
