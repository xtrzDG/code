"""The fingerprint of a deletion certificate's facts."""

import hashlib
import json

from app.schemas.domain.business_closures import BusinessDeletionDocument
from app.schemas.typings.business_closures.constrained_strings import (
    DeletionCertificateDigest,
)

CERTIFIED_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "deleted_business_id",
        "business_name",
        "reason",
        "requested_at",
        "started_at",
        "completed_at",
        "deprovisioned",
        "processor_erasure_jobs",
        "erased_files",
        "erased_rows",
        "retained_rows",
    }
)


def certificate_digest(entry: BusinessDeletionDocument) -> DeletionCertificateDigest:
    """
    SHA-256 of the certified facts as canonical JSON (sorted keys, no
    spaces): the same entry always prints the same fingerprint, and any
    change to what it certifies changes it.
    """

    facts: dict[str, object] = entry.model_dump(mode="json", include=CERTIFIED_FIELDS)
    canonical: str = json.dumps(facts, sort_keys=True, separators=(",", ":"))
    return DeletionCertificateDigest(
        hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    )
