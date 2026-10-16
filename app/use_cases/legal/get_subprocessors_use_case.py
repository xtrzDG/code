from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.subprocessor_registries import SubprocessorRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.legal import (
    SubprocessorChange,
    SubprocessorChangeView,
    SubprocessorEntry,
    SubprocessorListQuery,
    SubprocessorListView,
    SubprocessorView,
)
from app.schemas.typings.legal.constrained_integers import SubprocessorNoticeDays
from app.schemas.typings.legal.strings import (
    SubprocessorLocation,
    SubprocessorName,
    SubprocessorPersonalData,
    SubprocessorPurpose,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.legal.subprocessor_dates import (
    change_date,
    is_in_force,
    notice_opens_on,
    to_day,
    utc_day,
)
from app.utilities.legal.subprocessor_table import table_language
from app.utilities.localization.cldr_language_names import ENGLISH_LOCALE_IDENTIFIER


class GetSubprocessorsUseCase(
    UseCaseContract[SubprocessorListQuery, SubprocessorListView]
):
    """
    GET /v1/legal/subprocessors (public): the platform's sub-processors
    from the registry that also renders the DPA's section 8, in English,
    Russian or Georgian (other languages read English). The list holds
    every sub-processor in use today and every announced addition (not in
    force yet); one that left the list is gone from the day it left. The
    changes still ahead come with the day owners hear of them.
    """

    def __init__(
        self,
        subprocessor_registry: SubprocessorRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._registry: SubprocessorRegistryContract = subprocessor_registry
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SubprocessorListQuery) -> SubprocessorListView:
        language: LanguageTag = table_language(
            input_data.language or LanguageTag(ENGLISH_LOCALE_IDENTIFIER)
        )
        today: date = utc_day(self._wall_clock.now_unix())
        notice_days: SubprocessorNoticeDays = self._registry.notice_days()
        entries: list[SubprocessorEntry] = [
            entry
            for entry in self._registry.list_entries()
            if entry.removed_on is None or today < to_day(entry.removed_on)
        ]
        names: dict[str, SubprocessorName] = {
            str(entry.key): SubprocessorName(
                str(self._resolver.resolve(entry.name, language))
            )
            for entry in self._registry.list_entries()
        }
        return SubprocessorListView(
            language=language,
            as_of=change_date(today),
            notice_days=notice_days,
            subprocessors=[self._view(entry, language, today) for entry in entries],
            upcoming_changes=[
                change_view(change, names[str(change.subprocessor)], notice_days)
                for change in self._registry.list_changes()
                if to_day(change.effective_on) > today
            ],
        )

    def _view(
        self, entry: SubprocessorEntry, language: LanguageTag, today: date
    ) -> SubprocessorView:
        resolve = self._resolver.resolve
        return SubprocessorView(
            key=entry.key,
            name=SubprocessorName(str(resolve(entry.name, language))),
            purpose=SubprocessorPurpose(str(resolve(entry.purpose, language))),
            personal_data=SubprocessorPersonalData(
                str(resolve(entry.personal_data, language))
            ),
            location=SubprocessorLocation(str(resolve(entry.location, language))),
            added_on=entry.added_on,
            removed_on=entry.removed_on,
            is_in_force=is_in_force(entry, today),
        )


def change_view(
    change: SubprocessorChange,
    name: SubprocessorName,
    notice_days: SubprocessorNoticeDays,
) -> SubprocessorChangeView:
    return SubprocessorChangeView(
        key=change.key,
        kind=change.kind,
        subprocessor=change.subprocessor,
        name=name,
        effective_on=change.effective_on,
        announced_on=change.announced_on,
        notice_from=change_date(notice_opens_on(change, notice_days)),
    )
