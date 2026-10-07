from app.contracts.subprocessor_registries import SubprocessorRegistryContract
from app.registries.legal.subprocessor_catalog import (
    CLIENT_MODULES_WITHOUT_SUBPROCESSOR,
    SUBPROCESSOR_NOTICE_DAYS,
    SUBPROCESSORS,
)
from app.schemas.constants.legal import SubprocessorChangeKind
from app.schemas.dto.legal import SubprocessorChange, SubprocessorEntry
from app.schemas.typings.legal.constrained_integers import SubprocessorNoticeDays
from app.schemas.typings.legal.constrained_strings import (
    ClientModuleName,
    SubprocessorChangeDate,
    SubprocessorChangeKey,
)
from app.schemas.typings.legal.strings import ClientModuleExclusionReason
from app.utilities.legal.subprocessor_dates import to_day


class SubprocessorRegistry(SubprocessorRegistryContract):
    """
    The sub-processor list kept in code (`subprocessor_catalog.py`). The
    entries are checked when the registry is built: unique keys, a removal
    after the addition, and every change after the original list announced
    at least the notice period ahead, so a list that would break the DPA's
    promise cannot ship.
    """

    def __init__(
        self,
        entries: tuple[SubprocessorEntry, ...] = SUBPROCESSORS,
        notice_days: SubprocessorNoticeDays = SUBPROCESSOR_NOTICE_DAYS,
        client_modules_without_subprocessor: dict[
            ClientModuleName, ClientModuleExclusionReason
        ]
        | None = None,
    ) -> None:
        check_entries(entries, notice_days)
        self._entries: tuple[SubprocessorEntry, ...] = entries
        self._notice_days: SubprocessorNoticeDays = notice_days
        self._client_module_exclusions: dict[
            ClientModuleName, ClientModuleExclusionReason
        ] = (
            CLIENT_MODULES_WITHOUT_SUBPROCESSOR
            if client_modules_without_subprocessor is None
            else client_modules_without_subprocessor
        )

    def list_entries(self) -> list[SubprocessorEntry]:
        return list(self._entries)

    def list_changes(self) -> list[SubprocessorChange]:
        changes: list[SubprocessorChange] = []
        for entry in self._entries:
            if entry.addition_announced_on is not None:
                changes.append(
                    build_change(
                        entry,
                        SubprocessorChangeKind.ADDED,
                        entry.added_on,
                        entry.addition_announced_on,
                    )
                )
            if entry.removed_on is not None and entry.removal_announced_on is not None:
                changes.append(
                    build_change(
                        entry,
                        SubprocessorChangeKind.REMOVED,
                        entry.removed_on,
                        entry.removal_announced_on,
                    )
                )

        return sorted(
            changes, key=lambda change: (str(change.effective_on), str(change.key))
        )

    def notice_days(self) -> SubprocessorNoticeDays:
        return self._notice_days

    def client_modules_without_subprocessor(
        self,
    ) -> dict[ClientModuleName, ClientModuleExclusionReason]:
        return dict(self._client_module_exclusions)


def build_change(
    entry: SubprocessorEntry,
    kind: SubprocessorChangeKind,
    effective_on: SubprocessorChangeDate,
    announced_on: SubprocessorChangeDate,
) -> SubprocessorChange:
    return SubprocessorChange(
        key=SubprocessorChangeKey(f"{entry.key}-{kind.value}-{effective_on}"),
        kind=kind,
        subprocessor=entry.key,
        effective_on=effective_on,
        announced_on=announced_on,
    )


def check_entries(
    entries: tuple[SubprocessorEntry, ...], notice_days: SubprocessorNoticeDays
) -> None:
    """Raises ValueError for a list that would break the DPA's promises."""

    keys: list[str] = [str(entry.key) for entry in entries]
    duplicates: set[str] = {key for key in keys if keys.count(key) > 1}
    if duplicates:
        raise ValueError(f"Sub-processors listed twice: {sorted(duplicates)}")

    for entry in entries:
        for missing in missing_texts(entry):
            raise ValueError(f"{entry.key}: no English {missing}")

        if entry.removed_on is not None:
            if to_day(entry.removed_on) <= to_day(entry.added_on):
                raise ValueError(f"{entry.key}: removed before it was added")
            if entry.removal_announced_on is None:
                raise ValueError(f"{entry.key}: a removal must be announced")
            check_notice(
                entry, entry.removed_on, entry.removal_announced_on, notice_days
            )

        if entry.addition_announced_on is not None:
            check_notice(
                entry, entry.added_on, entry.addition_announced_on, notice_days
            )


def check_notice(
    entry: SubprocessorEntry,
    effective_on: SubprocessorChangeDate,
    announced_on: SubprocessorChangeDate,
    notice_days: SubprocessorNoticeDays,
) -> None:
    ahead: int = (to_day(effective_on) - to_day(announced_on)).days
    if ahead < int(notice_days):
        raise ValueError(
            f"{entry.key}: the change on {effective_on} is announced {ahead} days "
            f"ahead; the DPA promises {int(notice_days)}"
        )


def missing_texts(entry: SubprocessorEntry) -> list[str]:
    texts = {
        "name": entry.name,
        "purpose": entry.purpose,
        "personal data": entry.personal_data,
        "location": entry.location,
    }
    return [
        field
        for field, text in texts.items()
        if "en" not in {str(language) for language in text.values}
    ]
