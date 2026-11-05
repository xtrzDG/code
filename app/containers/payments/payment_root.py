from functools import cached_property

from app.containers.payments.payment_dependencies import PaymentDependencies
from app.containers.payments.payment_use_case_factories import (
    PaymentUseCaseFactories,
)


class PaymentRoot:
    """
    The typed composition root of the payments context (ADR 0010, like
    app/containers/feedback/): plain Python that builds the provider of
    each country, checkout, the payment webhooks of Flitt and Stripe, the
    card on file and the retries of declined charges from
    PaymentDependencies, checked by mypy and pyright without a single
    `# type: ignore`. The dependency graph holds one root
    (UseCasesContainer.payment_root) and exposes the use cases its
    orchestrators call (BillingOrchestratorsContainer).
    """

    def __init__(self, dependencies: PaymentDependencies) -> None:
        self._dependencies: PaymentDependencies = dependencies

    @cached_property
    def use_cases(self) -> PaymentUseCaseFactories:
        return PaymentUseCaseFactories(self._dependencies)
