from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.facilitators.invoicing.billing_document_facilitator import (
    BillingDocumentFacilitator,
)
from app.facilitators.invoicing.billing_email_attachments_facilitator import (
    BillingEmailAttachmentsFacilitator,
)
from app.facilitators.invoicing.invoice_issuing_facilitator import (
    InvoiceIssuingFacilitator,
)


class InvoicingFacilitatorsContainer(containers.DeclarativeContainer):
    """
    Invoicing (migration 1114): numbering an invoice with its parties and
    VAT, the invoice and receipt PDFs, and the PDFs an outbox e-mail to the
    billing contact carries. A child of FacilitatorsContainer, which names
    them flat (`facilitators.invoice_issuing_facilitator`).
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]

    invoice_issuing_facilitator: Singleton[InvoiceIssuingFacilitator] = Singleton(
        InvoiceIssuingFacilitator,
        billing_profile_repo=repositories.billing_profile_repo,
        invoice_counter_repo=repositories.invoice_counter_repo,
        tax_policy_registry=registries.tax_policy_registry,
        seller=config.app_settings.provided.seller,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    billing_document_facilitator: Singleton[BillingDocumentFacilitator] = Singleton(
        BillingDocumentFacilitator,
        layout_transformer=transformers.billing_document_layout_transformer,
        renderer=adapters.invoice_document_renderer,
    )
    billing_email_attachments_facilitator: Singleton[
        BillingEmailAttachmentsFacilitator
    ] = Singleton(
        BillingEmailAttachmentsFacilitator,
        business_repo=repositories.business_repo,
        invoice_repo=repositories.invoice_repo,
        billing_documents=billing_document_facilitator,
    )
