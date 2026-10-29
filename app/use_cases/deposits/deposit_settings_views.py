"""A business's deposit settings, stored or default, as the cabinet reads them."""

from typed_time_provider import Microseconds

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import (
    DepositSettingsDocument,
    PaymentLink,
    TargetedDepositPolicy,
)
from app.schemas.dto.deposits.deposit_settings import (
    DepositPolicyView,
    DepositSettingsView,
    PaymentLinkView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.deposits.deposit_keys import deposit_settings_id_of
from app.utilities.money.money_math import get_currency_minor_unit_digits


def stored_or_default(
    settings: DepositSettingsDocument | None,
    business_id: BusinessId,
    now: Microseconds,
) -> DepositSettingsDocument:
    """The stored settings, else the defaults (off, an hour's hold, 24 hours)."""

    if settings is not None:
        return settings

    return DepositSettingsDocument(
        id=deposit_settings_id_of(business_id),
        business_id=business_id,
        created_at=now,
        updated_at=now,
    )


def build_settings_view(
    settings: DepositSettingsDocument, business: BusinessDocument
) -> DepositSettingsView:
    return DepositSettingsView(
        is_enabled=settings.is_enabled,
        hold_minutes=settings.hold_minutes,
        refund_cutoff_hours=settings.refund_cutoff_hours,
        currency_code=business.currency_code,
        currency_digits=get_currency_minor_unit_digits(business.currency_code),
        payment_links=[link_view(link) for link in settings.payment_links],
        default_payment_link_id=settings.default_payment_link_id,
        policies=[policy_view(entry) for entry in settings.policies],
    )


def link_view(link: PaymentLink) -> PaymentLinkView:
    return PaymentLinkView(
        id=link.id,
        label=link.label,
        kind=link.kind,
        host=link.host,
        preview=link.preview,
        is_sealed=link.sealed_address is not None,
    )


def policy_view(entry: TargetedDepositPolicy) -> DepositPolicyView:
    return DepositPolicyView(
        target=entry.target,
        resource_id=entry.resource_id,
        service_item_id=entry.service_item_id,
        rule=entry.policy.rule,
        amount_minor=entry.policy.amount_minor,
        percent=entry.policy.percent,
        currency_code=entry.policy.currency_code,
        min_party_size=entry.policy.min_party_size,
        payment_link_id=entry.policy.payment_link_id,
    )
