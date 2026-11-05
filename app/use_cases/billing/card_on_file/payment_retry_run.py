"""One retry of a declined automatic charge: claimed once, charged, told."""

import logging

from typed_time_provider import Microseconds

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.payment_methods import (
    DunningNoticeFacilitatorContract,
    PaymentRetryRepoContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.payments import (
    DunningNoticeKind,
    PaymentProvider,
    PaymentRetryOutcome,
    PaymentStatus,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_retries import PaymentRetryAttemptDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_retries import (
    DunningNotice,
    PaymentRetryRequest,
    PaymentRetryResult,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import PaymentRetryAttempt
from app.schemas.typings.billing.strings import PaymentCardToken
from app.use_cases.billing.payment_webhook.payment_failure_notice import (
    invoice_amount,
)
from app.utilities.billing.dunning_schedule import (
    LAST_RETRY_ATTEMPT,
    find_next_retry_at,
    list_earlier_attempts,
    retry_due_at,
)
from app.utilities.billing.payment_retry_identity import derive_payment_retry_id

logger: logging.Logger = logging.getLogger(__name__)

OUTCOME_BY_STATUS: dict[PaymentStatus, PaymentRetryOutcome] = {
    PaymentStatus.APPROVED: PaymentRetryOutcome.APPROVED,
    PaymentStatus.DECLINED: PaymentRetryOutcome.DECLINED,
    PaymentStatus.EXPIRED: PaymentRetryOutcome.DECLINED,
}


class PaymentRetryRun:
    """The steps of one retry, for `RetryFailedPaymentsUseCase`."""

    def __init__(
        self,
        payment_retry_repo: PaymentRetryRepoContract,
        payment_gateway: PaymentGatewayAdapterContract,
        secret_cipher: SecretCipherAdapterContract,
        dunning_notices: DunningNoticeFacilitatorContract,
    ) -> None:
        self._payment_retry_repo: PaymentRetryRepoContract = payment_retry_repo
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._dunning_notices: DunningNoticeFacilitatorContract = dunning_notices

    def claim(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        invoice: InvoiceDocument,
        schedule_order: PaymentOrderDocument,
        attempt: PaymentRetryAttempt,
        grace_start: Microseconds,
        now: Microseconds,
    ) -> PaymentRetryAttemptDocument | None:
        """
        The retry's row when this worker inserted it (None: another worker
        has it); earlier retries never made are recorded as skipped.
        """

        def row(
            number: PaymentRetryAttempt, outcome: PaymentRetryOutcome
        ) -> PaymentRetryAttemptDocument:
            amount = invoice_amount(invoice)
            return PaymentRetryAttemptDocument(
                id=derive_payment_retry_id(invoice.id, number),
                business_id=business.id,
                subscription_id=subscription.id,
                invoice_id=invoice.id,
                attempt=number,
                provider=schedule_order.provider,
                outcome=outcome,
                amount_minor=amount.amount_minor,
                currency_code=amount.currency_code,
                due_at=retry_due_at(grace_start, number, business.timezone),
                attempted_at=now,
                created_at=now,
                updated_at=now,
            )

        claimed: PaymentRetryAttemptDocument = row(attempt, PaymentRetryOutcome.CLAIMED)
        if not self._payment_retry_repo.claim(claimed):
            return None

        for earlier in list_earlier_attempts(attempt):
            self._payment_retry_repo.claim(row(earlier, PaymentRetryOutcome.SKIPPED))

        return claimed

    def charge(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        invoice: InvoiceDocument,
        schedule_order: PaymentOrderDocument,
        claimed: PaymentRetryAttemptDocument,
        grace_start: Microseconds,
    ) -> None:
        """Charge the card again, record how it went and tell the owners."""

        try:
            result: PaymentRetryResult = self._payment_gateway.retry_charge(
                PaymentRetryRequest(
                    provider=schedule_order.provider,
                    retry_id=claimed.id,
                    payment_order_id=schedule_order.id,
                    attempt=claimed.attempt,
                    amount=invoice_amount(invoice),
                    description=invoice.description,
                    language=business.owner_language,
                    failed_charge_reference=invoice.provider_reference,
                    card_token=self._card_token(schedule_order),
                )
            )
            claimed.outcome = OUTCOME_BY_STATUS.get(
                result.status, PaymentRetryOutcome.PROCESSING
            )
            claimed.payment_reference = result.payment_reference
            claimed.failure_reason = result.failure_reason
        except ValidationFailedError:
            claimed.outcome = PaymentRetryOutcome.NOT_POSSIBLE
        except ExternalServiceError:
            logger.warning("A payment retry did not reach the payment provider.")
            claimed.outcome = PaymentRetryOutcome.FAILED

        self._payment_retry_repo.save(claimed)
        notice: DunningNotice | None = self._notice(
            business, subscription, invoice, claimed, grace_start
        )
        if notice is not None:
            self._dunning_notices.send(business, notice)

    def _card_token(
        self, schedule_order: PaymentOrderDocument
    ) -> PaymentCardToken | None:
        if (
            schedule_order.provider is not PaymentProvider.FLITT
            or schedule_order.sealed_card_token is None
        ):
            return None

        return PaymentCardToken(
            str(self._secret_cipher.decrypt(schedule_order.sealed_card_token))
        )

    def _notice(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        invoice: InvoiceDocument,
        claimed: PaymentRetryAttemptDocument,
        grace_start: Microseconds,
    ) -> DunningNotice | None:
        if claimed.outcome is PaymentRetryOutcome.APPROVED:
            kind: DunningNoticeKind = DunningNoticeKind.PAYMENT_RECOVERED
        elif claimed.outcome is not PaymentRetryOutcome.DECLINED:
            return None
        elif int(claimed.attempt) >= int(LAST_RETRY_ATTEMPT):
            kind = DunningNoticeKind.LAST_RETRY_DECLINED
        else:
            kind = DunningNoticeKind.RETRY_DECLINED

        next_retry_at: Microseconds | None = (
            find_next_retry_at(grace_start, claimed.attempt, business.timezone)
            if kind is DunningNoticeKind.RETRY_DECLINED
            else None
        )
        return DunningNotice(
            business_id=business.id,
            kind=kind,
            invoice_id=invoice.id,
            attempt=claimed.attempt,
            amount=invoice_amount(invoice),
            grace_until=subscription.grace_until,
            next_retry_at=next_retry_at,
        )
