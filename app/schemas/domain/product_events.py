from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.analytics import (
    ProductEventName,
    ProductEventSource,
    TunnelStepKey,
)
from app.schemas.constants.billing import BillingPeriod, PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.setup import ApplyAttentionCode
from app.schemas.constants.users import LoginMethod
from app.schemas.typings.analytics.constrained_integers import (
    MonthlyRecurringAmountMinor,
)
from app.schemas.typings.analytics.prefixed_id import ProductEventId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.users.prefixed_id import UserId


class ProductEventProperties(PersistentDocument):
    """
    The typed facts of a product event; each event name fills the ones it
    needs and leaves the rest empty:

    - tunnel steps: `tunnel_step`;
    - a blocked launch: `attention_codes`;
    - a connected channel: `channel`;
    - the agreement: `dpa_version`;
    - signing up and in: `login_method`;
    - billing steps: `plan_key` (after the step), `previous_plan_key` (a
      plan change), `billing_period`, `monthly_amount` and `currency_code`
      (what the subscription brings a month after the step) and
      `trial_ends_at` (a trial).

    Never free text and never a customer's data.
    """

    tunnel_step: TunnelStepKey | None = None
    attention_codes: list[ApplyAttentionCode] = Field(
        default_factory=list[ApplyAttentionCode]
    )
    channel: ChannelKind | None = None
    dpa_version: DpaDocumentVersion | None = None
    login_method: LoginMethod | None = None
    plan_key: PlanKey | None = None
    previous_plan_key: PlanKey | None = None
    billing_period: BillingPeriod | None = None
    monthly_amount: MonthlyRecurringAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    trial_ends_at: Microseconds | None = None


class ProductEventDocument(BaseDocument):
    """
    One step of an owner's way from sign-up to paying (first-party product
    analytics; the founder's GET /v1/admin/metrics reads them).

    `occurred_at` is when the step happened (a milestone noticed later, or
    a step the reconciliation derived from older records, keeps its real
    time); `created_at` is when it was written. The owner (`user_id`) and
    the business are named when known: a sign-in has no business, a
    payment webhook no user.
    """

    id: ProductEventId
    name: ProductEventName
    occurred_at: Microseconds
    source: ProductEventSource
    user_id: UserId | None = None
    business_id: BusinessId | None = None
    properties: ProductEventProperties = Field(default_factory=ProductEventProperties)
