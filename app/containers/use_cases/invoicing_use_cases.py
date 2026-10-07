from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.billing_profiles import (
    BillingProfileQuery,
    BillingProfileView,
    SaveBillingProfileCommand,
)
from app.schemas.dto.invoicing import (
    BillingDocumentFile,
    BillingDocumentQuery,
    BillingEmailsQueued,
)
from app.schemas.dto.payments import PaymentWebhookReceipt
from app.use_cases.billing.get_billing_document_use_case import (
    GetBillingDocumentUseCase,
)
from app.use_cases.billing.get_billing_profile_use_case import (
    GetBillingProfileUseCase,
)
from app.use_cases.billing.save_billing_profile_use_case import (
    SaveBillingProfileUseCase,
)
from app.use_cases.billing.send_payment_documents_use_case import (
    SendPaymentDocumentsUseCase,
)


class InvoicingUseCasesContainer(containers.DeclarativeContainer):
    """
    Invoicing (1114): the billing details, the invoice and receipt PDFs,
    and the e-mail of each paid invoice to the billing contact.
    """

    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_billing_profile_use_case: Factory[
        UseCaseContract[BillingProfileQuery, BillingProfileView]
    ] = Factory(
        GetBillingProfileUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        billing_profile_repo=repositories.billing_profile_repo,
        tax_policy_registry=registries.tax_policy_registry,
    )
    save_billing_profile_use_case: Factory[
        UseCaseContract[SaveBillingProfileCommand, BillingProfileView]
    ] = Factory(
        SaveBillingProfileUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        billing_profile_repo=repositories.billing_profile_repo,
        tax_policy_registry=registries.tax_policy_registry,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_billing_document_use_case: Factory[
        UseCaseContract[BillingDocumentQuery, BillingDocumentFile]
    ] = Factory(
        GetBillingDocumentUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        invoice_repo=repositories.invoice_repo,
        invoice_issuing=facilitators.invoice_issuing_facilitator,
        billing_documents=facilitators.billing_document_facilitator,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    send_payment_documents_use_case: Factory[
        UseCaseContract[PaymentWebhookReceipt, BillingEmailsQueued]
    ] = Factory(
        SendPaymentDocumentsUseCase,
        payment_order_repo=repositories.payment_order_repo,
        business_repo=repositories.business_repo,
        invoice_repo=repositories.invoice_repo,
        billing_profile_repo=repositories.billing_profile_repo,
        user_repo=repositories.user_repo,
        manager_notifier=facilitators.manager_notification_facilitator,
        email_transformer=transformers.billing_document_email_transformer,
    )
