"""Building the registry's texts: every sub-processor text is in en, ru and ka."""

from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.legal.constrained_strings import (
    ClientModuleName,
    SubprocessorChangeDate,
    SubprocessorKey,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue

# The DPA's first version: the original list is in force from this day,
# and only later changes are announced to owners.
ORIGINAL_LIST_DATE: SubprocessorChangeDate = SubprocessorChangeDate("2026-10-01")


def texts(en: str, ru: str, ka: str) -> LocalizedText:
    """One text of an entry in the DPA's three languages."""

    return LocalizedText(
        values={
            LanguageTag("en"): LocalizedTextValue(en),
            LanguageTag("ru"): LocalizedTextValue(ru),
            LanguageTag("ka"): LocalizedTextValue(ka),
        }
    )


def key(value: str) -> SubprocessorKey:
    return SubprocessorKey(value)


def modules(*names: str) -> list[ClientModuleName]:
    """The `app/clients` packages whose calls reach the sub-processor."""

    return [ClientModuleName(name) for name in names]
