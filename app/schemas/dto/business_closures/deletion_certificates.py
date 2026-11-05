"""What a deletion certificate is printed from."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.domain.business_closures import BusinessDeletionDocument
from app.schemas.typings.localization.constrained_strings import LanguageTag


class DeletionCertificateSource(ImmutableDTO):
    """A completed ledger entry, in the language the certificate is printed in."""

    entry: BusinessDeletionDocument
    language: LanguageTag
