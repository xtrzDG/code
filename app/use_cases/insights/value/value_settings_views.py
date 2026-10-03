"""Views of the value settings and of an owner's digest choices."""

from app.contracts.repositories.notification_repositories import (
    PushSubscriptionRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.domain.value_settings import (
    DigestPreferencesDocument,
    ValueSettingsDocument,
)
from app.schemas.dto.value.value_views import (
    DigestPreferencesView,
    ValueSettingsView,
)
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.insights.value.value_estimates import ValueEstimates
from app.utilities.notifications.staff_providers import is_provider_configured
from app.utilities.value.value_keys import (
    digest_preferences_id_of,
    value_settings_id_of,
)


def stored_settings_or_new(
    business: BusinessDocument,
    stored: ValueSettingsDocument | None,
) -> ValueSettingsDocument:
    if stored is not None:
        return stored

    return ValueSettingsDocument(
        id=value_settings_id_of(business.id), business_id=business.id
    )


def build_value_settings_view(
    business: BusinessDocument,
    settings: ValueSettingsDocument | None,
    estimates: ValueEstimates,
) -> ValueSettingsView:
    return ValueSettingsView(
        business_id=business.id,
        currency_code=business.currency_code,
        average_check_minor=None if settings is None else settings.average_check_minor,
        typical_check_minor=estimates.typical_check,
        value_basis=estimates.rates.basis,
    )


def stored_preferences_or_default(
    business: BusinessDocument,
    user_id: UserId,
    stored: DigestPreferencesDocument | None,
) -> DigestPreferencesDocument:
    """The owner's stored choices, else the defaults (weekly and monthly on)."""

    if stored is not None:
        return stored

    return DigestPreferencesDocument(
        id=digest_preferences_id_of(business.id, user_id),
        business_id=business.id,
        user_id=user_id,
    )


def build_digest_preferences_view(
    business: BusinessDocument,
    preferences: DigestPreferencesDocument,
    user_repo: UserRepoContract,
    push_subscription_repo: PushSubscriptionRepoContract,
    app_settings: AppSettings,
) -> DigestPreferencesView:
    user: UserDocument | None = user_repo.get(preferences.user_id)
    return DigestPreferencesView(
        business_id=business.id,
        is_daily_digest_on=preferences.is_daily_digest_on,
        is_weekly_digest_on=preferences.is_weekly_digest_on,
        is_monthly_report_on=preferences.is_monthly_report_on,
        email=None if user is None else user.email,
        is_email_ready=is_provider_configured(
            app_settings, ManagerContactChannel.EMAIL
        ),
        device_count=ListItemCount(
            len(push_subscription_repo.list_by_user(business.id, preferences.user_id))
        ),
    )
