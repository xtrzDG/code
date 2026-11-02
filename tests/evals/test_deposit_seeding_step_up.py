"""
The evals seed a business's deposits through the owner's use cases, which
ask for a fresh confirmation (step-up) before a payment page is added: the
seeding runs as the owner signed in just now, and nothing after it keeps
that session.
"""

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from scripts.eval_harness.deposit_seeding import DepositSpec, seed_deposits
from tests.e2e.harness import start_workshop
from tests.e2e.journeys import sign_in_and_create_restaurant


def test_seeded_deposits_pass_the_step_up_and_leave_no_session_behind() -> None:
    workshop = start_workshop()
    with workshop.client:
        _token, owner_id, business_id = sign_in_and_create_restaurant(workshop)
        container = workshop.container
        scope = container.utilities.storage_scope()
        with scope.platform_wide():
            business: BusinessDocument | None = container.repositories.business_repo().get(
                BusinessId(business_id)
            )
        assert business is not None

        with scope.scoped_to_business(business.id):
            seed_deposits(
                container,
                UserId(owner_id),
                business,
                DepositSpec(
                    page="https://pay.example.com/d?sum={amount}&ref={reference}",
                    per_guest="10",
                    min_party_size=6,
                ),
            )
            settings = container.repositories.deposit_settings_repo().get_by_business(
                business.id
            )

        assert settings is not None
        assert settings.is_enabled is True
        assert [str(link.host) for link in settings.payment_links] == ["pay.example.com"]
        assert container.utilities.session_assurance().current() is None
