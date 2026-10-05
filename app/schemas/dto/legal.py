"""The platform's legal texts and its sub-processor list (DPA section 8)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.legal import (
    LegalDocumentKind,
    ProcessorFlow,
    SubprocessorChangeKind,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.compliance.strings import (
    LegalDocumentMarkdown,
    LegalDocumentTitle,
)
from app.schemas.typings.legal.booleans import (
    HasLegalPlaceholders,
    IsSubprocessorInForce,
)
from app.schemas.typings.legal.constrained_integers import SubprocessorNoticeDays
from app.schemas.typings.legal.constrained_strings import (
    ClientModuleName,
    LegalDocumentVersion,
    SubprocessorChangeDate,
    SubprocessorChangeKey,
    SubprocessorKey,
)
from app.schemas.typings.legal.strings import (
    SubprocessorLocation,
    SubprocessorName,
    SubprocessorPersonalData,
    SubprocessorPurpose,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag


class SubprocessorEntry(ImmutableDTO):
    """
    One sub-processor in the registry (app/registries/legal): its texts in
    every language the DPA has, the `app/clients` packages that reach it,
    and when it joined (`added_on`, the DPA's first version for the
    original list) and leaves the list (`removed_on`, the first day it is
    no longer used). A change after the original list carries the day it
    was announced, at least the notice period ahead. `flows` are the data
    flows its purpose covers; `chat_provider_flows` those it covers only
    while it is the provider of the assistant's replies ("only when the
    Provider switches the model"). The platform refuses to start in
    production when a configured flow reaches a provider whose entries in
    force do not cover it (`processor_coverage.py`). A new purpose of a
    listed provider is an entry of its own, announced like an addition.
    """

    key: SubprocessorKey
    name: LocalizedText
    purpose: LocalizedText
    personal_data: LocalizedText
    location: LocalizedText
    client_modules: list[ClientModuleName] = Field(
        default_factory=list[ClientModuleName]
    )
    flows: list[ProcessorFlow] = Field(default_factory=list[ProcessorFlow])
    chat_provider_flows: list[ProcessorFlow] = Field(
        default_factory=list[ProcessorFlow]
    )
    added_on: SubprocessorChangeDate
    addition_announced_on: SubprocessorChangeDate | None = None
    removed_on: SubprocessorChangeDate | None = None
    removal_announced_on: SubprocessorChangeDate | None = None


class SubprocessorChange(ImmutableDTO):
    """An announced addition or removal of a sub-processor, derived from its entry."""

    key: SubprocessorChangeKey
    kind: SubprocessorChangeKind
    subprocessor: SubprocessorKey
    effective_on: SubprocessorChangeDate
    announced_on: SubprocessorChangeDate


class SubprocessorListQuery(ImmutableDTO):
    """The sub-processor list in a language (else its base language, else English)."""

    language: LanguageTag | None = None


class SubprocessorView(ImmutableDTO):
    """One sub-processor as owners and visitors read it."""

    key: SubprocessorKey
    name: SubprocessorName
    purpose: SubprocessorPurpose
    personal_data: SubprocessorPersonalData
    location: SubprocessorLocation
    added_on: SubprocessorChangeDate
    removed_on: SubprocessorChangeDate | None = None
    is_in_force: IsSubprocessorInForce


class SubprocessorChangeView(ImmutableDTO):
    """
    A change of the list that has not taken effect yet: owners are told
    from `notice_from` (the notice period before `effective_on`).
    """

    key: SubprocessorChangeKey
    kind: SubprocessorChangeKind
    subprocessor: SubprocessorKey
    name: SubprocessorName
    effective_on: SubprocessorChangeDate
    announced_on: SubprocessorChangeDate
    notice_from: SubprocessorChangeDate


class SubprocessorListView(ImmutableDTO):
    """
    GET /v1/legal/subprocessors: every sub-processor the list names today
    or has announced (an announced one is not in force yet; a leaving one
    shows its last day), and the changes still ahead. The DPA's section 8
    table is rendered from the same registry.
    """

    language: LanguageTag
    as_of: SubprocessorChangeDate
    notice_days: SubprocessorNoticeDays
    subprocessors: list[SubprocessorView]
    upcoming_changes: list[SubprocessorChangeView]


class LegalDocumentQuery(ImmutableDTO):
    """
    One legal text: the version in force today when `version` is None, in
    the language asked for (else its base language, else English).
    """

    kind: LegalDocumentKind
    language: LanguageTag | None = None
    version: LegalDocumentVersion | None = None


class LegalDocumentView(ImmutableDTO):
    """
    GET /v1/legal/{terms|privacy|cookies}: the text of one version.

    `version` is the day it took effect. `upcoming_version` is a newer text
    already published that takes effect later (owners can read it ahead).
    `has_placeholders` is true while the template still has fields in
    square brackets for the operator and its lawyer to fill.
    """

    kind: LegalDocumentKind
    version: LegalDocumentVersion
    language: LanguageTag
    available_languages: list[LanguageTag]
    title: LegalDocumentTitle
    text: LegalDocumentMarkdown
    has_placeholders: HasLegalPlaceholders
    upcoming_version: LegalDocumentVersion | None = None
