"""The DPA status of a business, as the status and acceptance use cases give it."""

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import DpaAcceptanceDocument
from app.schemas.dto.compliance import DpaAcceptanceView, DpaStatusView
from app.schemas.typings.compliance.booleans import IsDpaAccepted
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.utilities.compliance.dpa_versions import acceptance_due_on
from app.utilities.compliance.legal_endpoints import build_dpa_document_url


def dpa_status_view(
    business: BusinessDocument,
    version: DpaDocumentVersion,
    acceptances: list[DpaAcceptanceDocument],
    has_text: bool,
) -> DpaStatusView:
    """
    `acceptances` oldest first. A business that accepted an earlier version
    but not `version` needs to accept again, by 30 days after its date.
    """

    latest: DpaAcceptanceDocument | None = acceptances[-1] if acceptances else None
    is_accepted: IsDpaAccepted = business.dpa_version_accepted == version or any(
        acceptance.document_version == version for acceptance in acceptances
    )
    accepted_before: bool = (
        latest is not None or business.dpa_version_accepted is not None
    )
    needs_reacceptance: bool = accepted_before and not is_accepted
    return DpaStatusView(
        business_id=business.id,
        current_document_version=version,
        is_current_version_accepted=is_accepted,
        needs_reacceptance=needs_reacceptance,
        acceptance_due_on=acceptance_due_on(version) if needs_reacceptance else None,
        latest_acceptance=None
        if latest is None
        else DpaAcceptanceView(
            id=latest.id,
            document_version=latest.document_version,
            accepted_by=latest.accepted_by,
            accepted_at=latest.accepted_at,
        ),
        document_url=build_dpa_document_url(version) if has_text else None,
    )
