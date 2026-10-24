"""The cabinet's deposit settings: payment pages, policies, the hold."""

from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field, model_validator

from app.schemas.constants.deposits import DepositRule, DepositTarget, PaymentLinkKind
from app.schemas.typings.billing.constrained_integers import CurrencyMinorUnitDigits
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deposits.booleans import (
    AreDepositsEnabled,
    IsPaymentLinkSealed,
)
from app.schemas.typings.deposits.constrained_integers import (
    DepositAmountMinor,
    DepositHoldMinutes,
    DepositPercent,
    DepositRefundCutoffHours,
)
from app.schemas.typings.deposits.constrained_strings import (
    PaymentLinkAddressInput,
    PaymentLinkLabel,
)
from app.schemas.typings.deposits.prefixed_id import PaymentLinkId
from app.schemas.typings.deposits.strings import PaymentLinkHost, PaymentLinkPreview
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.users.prefixed_id import UserId


class PaymentLinkView(ImmutableDTO):
    """
    A payment page as the cabinet shows it: one that carries a key is
    `is_sealed` and shows only its host and path.
    """

    id: PaymentLinkId
    label: PaymentLinkLabel
    kind: PaymentLinkKind
    host: PaymentLinkHost
    preview: PaymentLinkPreview
    is_sealed: IsPaymentLinkSealed


class DepositPolicyView(ImmutableDTO):
    """One policy and what it applies to (amounts in minor units)."""

    target: DepositTarget
    resource_id: ResourceId | None = None
    service_item_id: KnowledgeItemId | None = None
    rule: DepositRule
    amount_minor: DepositAmountMinor | None = None
    percent: DepositPercent | None = None
    currency_code: CurrencyCode
    min_party_size: PartySize | None = None
    payment_link_id: PaymentLinkId | None = None


class DepositSettingsView(ImmutableDTO):
    """
    A business's deposits, with its currency and that currency's digits so
    the cabinet turns minor units into the amounts people type.
    """

    is_enabled: AreDepositsEnabled
    hold_minutes: DepositHoldMinutes
    refund_cutoff_hours: DepositRefundCutoffHours
    currency_code: CurrencyCode
    currency_digits: CurrencyMinorUnitDigits
    payment_links: list[PaymentLinkView] = Field(default_factory=list[PaymentLinkView])
    default_payment_link_id: PaymentLinkId | None = None
    policies: list[DepositPolicyView] = Field(default_factory=list[DepositPolicyView])


class DepositSettingsRequest(ImmutableDTO):
    """
    The owner's choices: deposits on or off, how long a held place waits,
    until when before the start a cancellation is refunded, and the
    template that serves policies naming no page (null keeps the current
    one).
    """

    is_enabled: AreDepositsEnabled = False
    hold_minutes: DepositHoldMinutes = DepositHoldMinutes(60)
    refund_cutoff_hours: DepositRefundCutoffHours = DepositRefundCutoffHours(24)
    default_payment_link_id: PaymentLinkId | None = None


class PaymentLinkInput(ImmutableDTO):
    """A payment page to add: its name, whether it is fixed or a template."""

    label: PaymentLinkLabel
    kind: PaymentLinkKind
    address: PaymentLinkAddressInput


class DepositPolicyInput(ImmutableDTO):
    """A policy as the owner sets it, in the business currency's minor units."""

    rule: DepositRule
    amount_minor: DepositAmountMinor | None = None
    percent: DepositPercent | None = None
    min_party_size: PartySize | None = None
    payment_link_id: PaymentLinkId | None = None

    @model_validator(mode="after")
    def require_the_rule_input(self) -> Self:
        if self.rule is DepositRule.PERCENT_OF_VALUE:
            if self.percent is None or self.amount_minor is not None:
                raise ValueError("A percent policy names a percent and no amount.")
        elif self.amount_minor is None or self.percent is not None:
            raise ValueError("A fixed policy names an amount and no percent.")

        return self


class DepositPolicyRequest(ImmutableDTO):
    """
    Set (or, with `policy` null, remove) the policy of a resource, a
    service or the banquets; the target decides which id is needed.
    """

    target: DepositTarget
    resource_id: ResourceId | None = None
    service_item_id: KnowledgeItemId | None = None
    policy: DepositPolicyInput | None = None

    @model_validator(mode="after")
    def require_the_target_id(self) -> Self:
        given: tuple[bool, bool] = (
            self.resource_id is not None,
            self.service_item_id is not None,
        )
        expected: tuple[bool, bool] = (
            self.target is DepositTarget.RESOURCE,
            self.target is DepositTarget.SERVICE,
        )
        if given != expected:
            raise ValueError("Name exactly the id the target needs.")

        return self


class DepositSettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class UpdateDepositSettingsCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: DepositSettingsRequest


class AddPaymentLinkCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    link: PaymentLinkInput


class RemovePaymentLinkCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    link_id: PaymentLinkId


class SetDepositPolicyCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: DepositPolicyRequest
