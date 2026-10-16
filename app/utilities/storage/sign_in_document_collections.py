"""
The catalog entries of users and sign-in (platform-wide collections): the
login codes, sessions and two-factor sign-in (1082). Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py).
"""

from app.schemas.domain.mfa import (
    MfaChallengeDocument,
    RecoveryCodeDocument,
    TotpFactorDocument,
)
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

SIGN_IN_DOCUMENT_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(DocumentCollectionName("users"), UserDocument),
    DocumentCollectionDefinition(
        DocumentCollectionName("otp_challenges"), OtpChallengeDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("user_sessions"), UserSessionDocument
    ),
    # Two-factor sign-in: authenticators, recovery codes and the second
    # step of a sign-in (1082).
    DocumentCollectionDefinition(
        DocumentCollectionName("totp_factors"), TotpFactorDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("recovery_codes"), RecoveryCodeDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("mfa_challenges"), MfaChallengeDocument
    ),
)
