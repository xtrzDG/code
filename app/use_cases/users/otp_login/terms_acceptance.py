"""The terms of service a person accepts by signing in (the code step's line)."""

import logging

from typed_time_provider import Microseconds

from app.contracts.legal_text_registries import LegalTextRegistryContract
from app.schemas.constants.legal import LegalDocumentKind
from app.schemas.domain.users import UserDocument
from app.schemas.typings.legal.constrained_strings import LegalDocumentVersion
from app.utilities.legal.subprocessor_dates import utc_day

logger: logging.Logger = logging.getLogger(__name__)


def record_terms_acceptance(
    user: UserDocument,
    shown_version: LegalDocumentVersion | None,
    legal_text_registry: LegalTextRegistryContract,
    now: Microseconds,
) -> None:
    """
    Store the terms version the sign-in page showed as accepted now. Only a
    version this build has a text of and that is in force (not a later one
    published ahead) counts, and an older page never takes a newer
    acceptance back; anything else keeps what is stored (the sign-in goes
    on: a stale page must not lock anyone out).
    """

    if shown_version is None:
        return

    if (
        not legal_text_registry.has_version(LegalDocumentKind.TERMS, shown_version)
        or str(shown_version) > utc_day(now).isoformat()
    ):
        logger.warning(
            "The sign-in page showed terms %s, which are not in force here.",
            shown_version,
        )
        return

    current: LegalDocumentVersion | None = user.accepted_terms_version
    if current is not None and str(current) >= str(shown_version):
        return

    user.accepted_terms_version = shown_version
    user.terms_accepted_at = now
