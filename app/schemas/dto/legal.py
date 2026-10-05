"""The platform's legal texts and its sub-processor list (DPA section 8)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.legal import LegalDocumentKind, SubprocessorChangeKind
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.compliance.strings import (
    LegalDocumentMarkdown,
    LegalDocumentTitle,
)
from app.schemas.typings.invoicing.constrained_strings import (
    BillingAddressText,
    BillingLegalName,
    TaxpayerIdentificationNumber,
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
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.public_site.booleans import IsLegalTextDraft
from app.schemas.typings.users.constrained_strings import EmailAddress


class SubprocessorEntry(ImmutableDTO):
    """
    One sub-processor in the registry (app/registries/legal): its texts in
    every language the DPA has, the `app/clients` packages that reach it,
    and when it joined (`added_on`, the DPA's first version for the
    original list) and leaves the list (`removed_on`, the first day it is
    no longer used). A change after the original list carries the day it
    was announced, at least the notice period ahead.
    """

    key: SubprocessorKey
    name: LocalizedText
    purpose: LocalizedText
    personal_data: LocalizedText
    location: LocalizedText
    client_modules: list[ClientModuleName] = Field(
        default_factory=list[ClientModuleName]
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
    GET /v1/legal/{terms|privacy|cookies|security}: the text of one version.

    `version` is the day it took effect. `upcoming_version` is a newer text
    already published that takes effect later (owners can read it ahead).
    `has_placeholders` is true while the template still has fields in
    square brackets for the operator and its lawyer to fill; `is_draft`
    while it does or the operator has not declared the texts final
    (LEGAL_TEXTS_FINAL): the public pages then say it is a draft.
    """

    kind: LegalDocumentKind
    version: LegalDocumentVersion
    language: LanguageTag
    available_languages: list[LanguageTag]
    title: LegalDocumentTitle
    text: LegalDocumentMarkdown
    has_placeholders: HasLegalPlaceholders
    upcoming_version: LegalDocumentVersion | None = None
    is_draft: IsLegalTextDraft = True


class LegalOverviewQuery(ImmutableDTO):
    """GET /v1/legal/overview (no input)."""


class LegalOperatorView(ImmutableDTO):
    """
    Who provides the service, as the invoices name the seller (SELLER_*):
    a detail the operator has not set is null.
    """

    legal_name: BillingLegalName
    address: BillingAddressText | None = None
    email: EmailAddress | None = None
    tax_id: TaxpayerIdentificationNumber | None = None
    country_code: CountryCode


class LegalOverviewView(ImmutableDTO):
    """
    GET /v1/legal/overview: what the public legal and contact pages need
    besides the texts: whether the texts are still drafts
    (LEGAL_TEXTS_FINAL off), the data processing agreement's version in
    force (DPA_DOCUMENT_VERSION; its text is /v1/legal/dpa/{version}) and
    the operator's details.
    """

    is_draft: IsLegalTextDraft
    dpa_version: DpaDocumentVersion
    operator: LegalOperatorView
