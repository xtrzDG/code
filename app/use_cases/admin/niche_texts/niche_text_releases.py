"""
Publishing a version of a niche's texts: the draft, an earlier version's
texts (a revert) or none (a reset to the code template) become the next
version, the draft goes, and the platform's audit log names who published
which version of which niche.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.niche_text_repositories import NicheTextRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.niches import NicheKey, NicheTextReleaseKind
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.niche_texts import NicheTextEntry, NicheTextReleaseDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.niches.constrained_integers import NicheTextVersion
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.niches.niche_text_identity import release_id_for

NICHE_TEMPLATE_ENTITY: AuditEntityName = AuditEntityName("niche_template")


@dataclass(frozen=True, slots=True, kw_only=True)
class NicheTextPublication:
    """What the next version holds and who publishes it, from where, when."""

    niche_key: NicheKey
    kind: NicheTextReleaseKind
    entries: Sequence[NicheTextEntry]
    restored_version: NicheTextVersion | None = None
    admin_id: UserId
    client_ip_address: ClientIpAddress | None
    now: Microseconds


def publish_release(
    niche_text_repo: NicheTextRepoContract,
    audit_log_repo: AuditLogRepoContract,
    current: NicheTextReleaseDocument | None,
    publication: NicheTextPublication,
) -> NicheTextReleaseDocument:
    """
    Store the version after `current` and remove the niche's draft.

    Raises:
        ConflictError: another admin published that version a moment ago.
    """

    version = NicheTextVersion(1 if current is None else int(current.version) + 1)
    release = NicheTextReleaseDocument(
        id=release_id_for(publication.niche_key, version),
        niche_key=publication.niche_key,
        version=version,
        kind=publication.kind,
        entries=list(publication.entries),
        restored_version=publication.restored_version,
        published_by=publication.admin_id,
        created_at=publication.now,
        updated_at=publication.now,
    )
    if not niche_text_repo.add_release(release):
        raise ConflictError(
            f"Version {int(version)} of this niche was published a moment ago: "
            "reload the editor and try again."
        )

    niche_text_repo.delete_draft(publication.niche_key)
    audit_log_repo.append(
        AuditLogEntryDocument(
            actor_id=publication.admin_id,
            action=AuditAction.UPDATE,
            entity=NICHE_TEMPLATE_ENTITY,
            entity_id=AuditEntityReference(audit_reference(release)),
            ip_address=publication.client_ip_address,
            created_at=publication.now,
            updated_at=publication.now,
        )
    )
    return release


def audit_reference(release: NicheTextReleaseDocument) -> str:
    """
    "restaurant:v3:revert:v1": the niche, the version, how it was made and
    the version a revert went back to. About the platform: no business.
    """

    reference: str = (
        f"{release.niche_key.value}:v{int(release.version)}:{release.kind.value}"
    )
    if release.restored_version is not None:
        return f"{reference}:v{int(release.restored_version)}"

    return reference
