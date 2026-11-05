"""The security measures the DPA's section 9 promises, kept as data."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.legal.constrained_strings import (
    RepositoryPath,
    SecurityMeasureKey,
)


class SecurityMeasure(ImmutableDTO):
    """
    One technical or organisational measure of DPA section 9: its sentence
    in every language the DPA has, the code or documents that implement it
    (`implemented_by`, checked to exist), and the first DPA version that
    lists it (`listed_from`; a later version lists it too, an earlier one
    does not). `listed_until` is the first version that no longer lists it.
    """

    key: SecurityMeasureKey
    text: LocalizedText
    implemented_by: list[RepositoryPath] = Field(default_factory=list[RepositoryPath])
    listed_from: DpaDocumentVersion
    listed_until: DpaDocumentVersion | None = None
