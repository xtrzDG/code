from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.adapters.invoicing_collections_container import (
    InvoicingCollectionsContainer,
)
from app.repositories.invoicing_repositories import (
    BillingProfileRepository,
    InvoiceCounterRepository,
)
from app.repositories.payment_repositories import (
    PackageUsageWarningRepository,
    PaymentOrderRepository,
)


class BillingRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of payments and invoicing: checkout orders and
    package usage warnings (0003), billing details and invoice numbers
    (1114). `RepositoriesContainer` extends it, so they are read as
    `repositories.billing_profile_repo` like every other repository.
    """

    payment_collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    invoicing_collections: InvoicingCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    payment_order_repo: Singleton[PaymentOrderRepository] = Singleton(
        PaymentOrderRepository,
        collection=payment_collections.payment_order_collection,
    )
    package_usage_warning_repo: Singleton[PackageUsageWarningRepository] = Singleton(
        PackageUsageWarningRepository,
        collection=payment_collections.package_usage_warning_collection,
    )
    billing_profile_repo: Singleton[BillingProfileRepository] = Singleton(
        BillingProfileRepository,
        collection=invoicing_collections.billing_profile_collection,
    )
    invoice_counter_repo: Singleton[InvoiceCounterRepository] = Singleton(
        InvoiceCounterRepository,
        collection=invoicing_collections.invoice_counter_collection,
    )
