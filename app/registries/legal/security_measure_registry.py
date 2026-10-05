from app.contracts.security_measures import SecurityMeasureRegistryContract
from app.registries.legal.security_measures_access import ACCESS_MEASURES
from app.registries.legal.security_measures_data import DATA_MEASURES
from app.schemas.dto.security_measures import SecurityMeasure
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion

SECURITY_MEASURES: tuple[SecurityMeasure, ...] = (*ACCESS_MEASURES, *DATA_MEASURES)


class SecurityMeasureRegistry(SecurityMeasureRegistryContract):
    """
    The measures of DPA section 9 kept in code
    (`security_measures_access.py`, `security_measures_data.py`): the single
    source of the section in every DPA version from 2026-10-06 on
    (`scripts/render_subprocessor_table.py` writes it into the files). A
    version lists the measures in force on its date, compared as ISO dates.
    """

    def __init__(
        self, measures: tuple[SecurityMeasure, ...] = SECURITY_MEASURES
    ) -> None:
        keys: list[str] = [str(measure.key) for measure in measures]
        duplicates: set[str] = {key for key in keys if keys.count(key) > 1}
        if duplicates:
            raise ValueError(f"Security measures listed twice: {sorted(duplicates)}")

        self._measures: tuple[SecurityMeasure, ...] = measures

    def list_measures(self) -> list[SecurityMeasure]:
        return list(self._measures)

    def measures_of(self, version: DpaDocumentVersion) -> list[SecurityMeasure]:
        return [
            measure
            for measure in self._measures
            if str(measure.listed_from) <= str(version)
            and (
                measure.listed_until is None or str(version) < str(measure.listed_until)
            )
        ]
