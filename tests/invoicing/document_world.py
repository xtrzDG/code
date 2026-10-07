"""
The billing documents over the billing testbed: billing details, the
invoice and receipt PDFs (laid out for real; rendered by WeasyPrint or by
a renderer that hands the HTML back for the tests to read).
"""

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.invoicing import InvoiceDocumentRendererContract
from app.facilitators.invoicing.billing_document_facilitator import (
    BillingDocumentFacilitator,
)
from app.gateways.http.billing_document_routes import build_billing_document_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.schemas.typings.invoicing.strings import BillingDocumentHtml
from app.transformers.invoicing.billing_document_layout_transformer import (
    BillingDocumentLayoutTransformer,
)
from app.use_cases.billing.get_billing_document_use_case import (
    GetBillingDocumentUseCase,
)
from app.use_cases.billing.get_billing_profile_use_case import (
    GetBillingProfileUseCase,
)
from app.use_cases.billing.save_billing_profile_use_case import (
    SaveBillingProfileUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.billing.billing_fakes import TokenAuthenticationOperator, build_operator
from tests.billing.paid_world import PaidWorld


class HtmlEchoRenderer(InvoiceDocumentRendererContract):
    """Hands the laid-out HTML back as the "PDF", and keeps it."""

    def __init__(self) -> None:
        self.pages: list[str] = []

    def render(self, html: BillingDocumentHtml) -> bytes:
        self.pages.append(str(html))
        return str(html).encode()


@dataclass(frozen=True)
class DocumentWorld:
    """A paid world with the billing document use cases and their router."""

    world: PaidWorld
    layout: BillingDocumentLayoutTransformer
    documents: BillingDocumentFacilitator
    get_document: GetBillingDocumentUseCase
    get_profile: GetBillingProfileUseCase
    save_profile: SaveBillingProfileUseCase

    def http_client(self) -> TestClient:
        testbed = self.world.testbed
        application = FastAPI()
        install_error_handlers(application)
        application.include_router(
            build_billing_document_router(
                get_billing_profile_operator=build_operator(self.get_profile),
                save_billing_profile_operator=build_operator(self.save_profile),
                get_billing_document_operator=build_operator(self.get_document),
                current_user=build_current_user_dependency(
                    TokenAuthenticationOperator(testbed.user_repo),
                    SessionAssuranceContext(),
                ),
            )
        )
        return TestClient(application)


def build_document_world(
    world: PaidWorld, renderer: InvoiceDocumentRendererContract
) -> DocumentWorld:
    testbed = world.testbed
    layout = BillingDocumentLayoutTransformer(LocalizedTextResolver())
    documents = BillingDocumentFacilitator(layout_transformer=layout, renderer=renderer)
    parts = testbed.invoicing
    return DocumentWorld(
        world=world,
        layout=layout,
        documents=documents,
        get_document=GetBillingDocumentUseCase(
            authorize_business_access=testbed.authorize,
            invoice_repo=testbed.invoice_repo,
            invoice_issuing=parts.invoice_issuing,
            billing_documents=documents,
            audit_log_repo=testbed.audit_log_repo,
            wall_clock=testbed.clock.wall_clock,
        ),
        get_profile=GetBillingProfileUseCase(
            authorize_business_access=testbed.authorize,
            billing_profile_repo=parts.billing_profile_repo,
            tax_policy_registry=parts.tax_policy_registry,
        ),
        save_profile=SaveBillingProfileUseCase(
            authorize_business_access=testbed.authorize,
            billing_profile_repo=parts.billing_profile_repo,
            tax_policy_registry=parts.tax_policy_registry,
            audit_log_repo=testbed.audit_log_repo,
            wall_clock=testbed.clock.wall_clock,
        ),
    )
