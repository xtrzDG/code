"""In-memory wiring of the billing slice shared by its tests.

Real registries (plans with the GEL price book, official rates), real
localization utilities, in-memory repositories, a recording notifier, an
adjustable clock and a Flitt sandbox behind httpx.MockTransport that checks
request signatures like Flitt does. Nothing touches the network.
The wiring is layered: infrastructure, then use cases; this module adds the
data builders and the HTTP client.
"""

import json
from collections.abc import Callable

from fastapi.testclient import TestClient
from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import PlanKey, SetupOption, UsageKind
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_ledger import BillingNotice, InvoiceDescriptionInput
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.payments import PaymentWebhookDelivery, PaymentWebhookReceipt
from app.schemas.typings.billing.constrained_integers import CostMicroUsd, UsageQuantity
from app.schemas.typings.billing.strings import (
    PaymentWebhookBody,
    PaymentWebhookContentType,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import UserDisplayName
from tests.billing.billing_http import build_billing_http_client
from tests.billing.billing_settings import (
    FLITT_MERCHANT_ID,
    GEORGIA,
    CountryPreset,
    sign_flitt_callback,
)
from tests.billing.billing_use_cases import BillingUseCases


class BillingTestbed(BillingUseCases):
    """Every billing and admin use case over in-memory storage."""

    def add_user(
        self,
        email: str | None = None,
        phone_number: str | None = None,
        locale: str = "en",
        is_platform_admin: bool = False,
        display_name: str | None = None,
    ) -> UserDocument:
        user = UserDocument(
            login_method=LoginMethod.EMAIL if email else LoginMethod.PHONE,
            email=None if email is None else EmailAddress(email),
            phone_number=None
            if phone_number is None
            else E164PhoneNumber(phone_number),
            locale=LanguageTag(locale),
            display_name=None
            if display_name is None
            else UserDisplayName(display_name),
            is_verified=True,
            is_platform_admin=is_platform_admin,
        )
        self.user_repo.save(user)
        return user

    def add_business(
        self,
        owner: UserDocument,
        country: CountryPreset = GEORGIA,
        plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
        name: str = "Funicular VR",
        staff: list[UserDocument] | None = None,
    ) -> BusinessDocument:
        members: list[BusinessMember] = [
            BusinessMember(user_id=owner.id, role=BusinessMemberRole.OWNER)
        ]
        members.extend(
            BusinessMember(user_id=member.id, role=BusinessMemberRole.STAFF)
            for member in staff or []
        )
        business = BusinessDocument(
            name=BusinessName(name),
            niche_key=NicheKey.ENTERTAINMENT,
            country_code=CountryCode(country.country_code),
            timezone=TimezoneName(country.timezone),
            currency_code=CurrencyCode(country.currency_code),
            languages=[LanguageTag(language) for language in country.languages],
            default_language=LanguageTag(country.languages[0]),
            owner_language=LanguageTag(country.owner_language),
            plan_key=plan_key,
            data_region=DataRegion.EU,
            members=members,
        )
        self.business_repo.save(business)
        return business

    def business(self, business_id: BusinessId) -> BusinessDocument:
        business: BusinessDocument | None = self.business_repo.get(business_id)
        assert business is not None
        return business

    def subscription(self, business_id: BusinessId) -> SubscriptionDocument:
        subscriptions = self.subscription_repo.list_by_business(business_id)
        assert len(subscriptions) == 1
        return subscriptions[0]

    def set_up_for_you(self, business_id: BusinessId) -> None:
        """The platform team sets this business up: the setup fee applies."""

        subscription = self.subscription(business_id)
        subscription.setup_option = SetupOption.DONE_FOR_YOU
        self.subscription_repo.save(subscription)

    def invoices(self, business_id: BusinessId) -> list[InvoiceDocument]:
        return sorted(
            self.invoice_repo.list_by_business(business_id),
            key=lambda invoice: (invoice.period_start, invoice.kind.value),
        )

    def record_usage(
        self,
        business_id: BusinessId,
        kind: UsageKind,
        quantity: int,
        cost_micro_usd: int = 0,
        conversation_id: ConversationId | None = None,
        occurred_at: Microseconds | None = None,
    ) -> None:
        moment: Microseconds = occurred_at or self.clock.now()
        self.usage_event_repo.append(
            UsageEventDocument(
                business_id=business_id,
                conversation_id=conversation_id,
                kind=kind,
                quantity=UsageQuantity(quantity),
                cost_micro_usd=CostMicroUsd(cost_micro_usd),
                occurred_at=moment,
                created_at=moment,
                updated_at=moment,
            )
        )

    def run_job(self, job: UseCaseContract[JobTick, JobReport], name: str) -> int:
        report: JobReport = job.run(
            JobTick(job_name=JobName(name), scheduled_at=self.clock.now())
        )
        return int(report.processed_count)

    def deliver_flitt_callback(
        self,
        parameters: dict[str, object],
        is_signed: bool = True,
        content_type: str = "application/json",
        encoder: Callable[[dict[str, object]], str] = json.dumps,
    ) -> PaymentWebhookReceipt:
        payload: dict[str, object] = (
            sign_flitt_callback(parameters) if is_signed else parameters
        )
        return self.process_webhook.run(
            PaymentWebhookDelivery(
                body=PaymentWebhookBody(encoder(payload)),
                content_type=PaymentWebhookContentType(content_type),
            )
        )

    def callback_parameters(
        self,
        payment_order: PaymentOrderDocument,
        order_status: str,
        payment_id: int = 900000001,
        amount: int | None = None,
        **extra: object,
    ) -> dict[str, object]:
        return {
            "order_id": str(payment_order.id),
            "merchant_id": int(FLITT_MERCHANT_ID),
            "order_status": order_status,
            "response_status": "success",
            "amount": (int(payment_order.amount_minor) if amount is None else amount),
            "currency": str(payment_order.currency_code),
            "payment_id": payment_id,
            "merchant_data": str(payment_order.id),
            "response_description": "",
            **extra,
        }

    def build_http_client(self) -> TestClient:
        return build_billing_http_client(self)


def bearer(user: UserDocument) -> dict[str, str]:
    return {"Authorization": f"Bearer {user.id}"}


def describe_notice(testbed: BillingTestbed, notice: BillingNotice) -> str:
    return str(testbed.notice_transformer.transform(notice))


def describe_invoice(
    testbed: BillingTestbed,
    description_input: InvoiceDescriptionInput,
) -> str:
    return str(testbed.invoice_description_transformer.transform(description_input))
