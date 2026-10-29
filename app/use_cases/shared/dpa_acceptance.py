"""
Whether an owner accepted the data processing agreement version in force,
the one answer the DPA status, the setup guide and the go-live gates give.

The business keeps the version an owner accepted last
(`BusinessDocument.dpa_version_accepted`, from schema version 5); a business
that accepted before that is answered by its acceptance records.
"""

from app.contracts.repositories.compliance_repositories import DpaAcceptanceRepoContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.compliance.booleans import IsDpaAccepted
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion


def is_dpa_version_accepted(
    business: BusinessDocument,
    version: DpaDocumentVersion,
    dpa_acceptance_repo: DpaAcceptanceRepoContract,
) -> IsDpaAccepted:
    if business.dpa_version_accepted == version:
        return True

    return any(
        acceptance.document_version == version
        for acceptance in dpa_acceptance_repo.list_by_business(business.id)
    )
