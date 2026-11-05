"""
An invoice that uses a client's credit is issued on the two database roles
(migration 1200): the credit lock's transaction is the platform's, so the
invoice gets its number from `invoice_counters`, which the tenant role may
not touch, while the business's own rows are read and written in its scope.
"""

from app.schemas.constants.billing import BillingCreditKind
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.dto.billing_ledger import DueInvoicesRequest
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.billing.constrained_integers import BillingCreditAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from tests.e2e.harness import Workshop, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import open_restaurant
from tests.storage.postgres_roles import RoleDatabase

CREDIT: BillingCreditAmountMinor = BillingCreditAmountMinor(1_000)


def grant_credit(workshop: Workshop, business_id: BusinessId, admin_id: UserId) -> None:
    container = workshop.container
    subscription = container.repositories.subscription_repo().list_by_business(
        business_id
    )[0]
    now = subscription.period_start
    container.repositories.billing_credit_repo().record(
        BillingCreditDocument(
            business_id=business_id,
            kind=BillingCreditKind.GRANTED,
            amount_minor=CREDIT,
            currency_code=subscription.currency_code,
            granted_by=admin_id,
            reason=AdminActionReason("Goodwill credit after an outage"),
            created_at=now,
            updated_at=now,
        )
    )


def test_an_invoice_with_credit_is_numbered_on_the_tenant_and_platform_roles(
    role_urls: RoleDatabase,
) -> None:
    workshop = start_workshop({**E2E_ENVIRONMENT, **role_urls.environment()})
    container = workshop.container
    storage_scope = container.utilities.storage_scope()
    with workshop.client:
        restaurant = open_restaurant(workshop)
        business_id = BusinessId(restaurant.business_id)
        # Checkout and the renewal job issue in the business's own scope.
        with storage_scope.scoped_to_business(business_id):
            grant_credit(workshop, business_id, UserId(restaurant.owner_id))
            business = container.repositories.business_repo().get(business_id)
            assert business is not None
            subscription = container.repositories.subscription_repo()
            current = subscription.list_by_business(business_id)[0]
            issued = container.use_cases.billing.issue_due_invoices_use_case().run(
                DueInvoicesRequest(
                    business=business,
                    subscription=current,
                    period_start=current.period_end,
                )
            )
            ledger = container.repositories.billing_credit_repo()
            used = [
                line
                for line in ledger.list_by_business(business_id)
                if line.kind is BillingCreditKind.USED
            ]

    credited = [invoice for invoice in issued if invoice.credit_minor is not None]
    assert len(credited) == 1
    assert credited[0].number is not None
    assert [int(line.amount_minor) for line in used] == [int(CREDIT)]
