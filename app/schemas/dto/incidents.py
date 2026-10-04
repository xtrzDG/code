"""
The platform admin's incident log: recording an incident (POST
/v1/admin/incidents), which for a data breach also tells the owners of
every affected business (DPA section 12.1), and listing the log.
"""

from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field, model_validator
from typed_time_provider import Microseconds

from app.schemas.constants.incidents import (
    IncidentKind,
    IncidentSeverity,
    IncidentStatus,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.incidents.constrained_integers import (
    AffectedRecordCount,
    AffectedSubjectCount,
    NotifiedOwnerCount,
)
from app.schemas.typings.incidents.constrained_strings import (
    BreachMeasuresText,
    BreachNatureText,
    IncidentTitle,
    LikelyConsequencesText,
    RecordCategoriesText,
    SubjectCategoriesText,
)
from app.schemas.typings.incidents.prefixed_id import IncidentId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId

# One request records an incident for at most this many businesses (each
# gets its owner notices and audit entry in the same request).
MAX_AFFECTED_BUSINESSES: int = 1000
NOTICE_FALLBACK_LANGUAGE: str = "en"


class IncidentNoticeInput(ImmutableDTO):
    """The DPA 12.1 texts of a breach notice in one language."""

    language: LanguageTag
    nature: BreachNatureText
    subject_categories: SubjectCategoriesText
    record_categories: RecordCategoriesText
    likely_consequences: LikelyConsequencesText
    measures: BreachMeasuresText


class CreateIncidentBody(ImmutableDTO):
    """
    POST /v1/admin/incidents. `started_at` is when the incident began,
    `detected_at` when the platform became aware of it (default: now).
    A data breach needs the notice: the approximate numbers of people and
    records concerned and the texts in English (and in any other language
    owners read, e.g. Georgian and Russian).
    """

    kind: IncidentKind
    severity: IncidentSeverity
    title: IncidentTitle
    started_at: Microseconds
    detected_at: Microseconds | None = None
    affected_business_ids: list[BusinessId] = Field(
        min_length=1, max_length=MAX_AFFECTED_BUSINESSES
    )
    approximate_subject_count: AffectedSubjectCount | None = None
    approximate_record_count: AffectedRecordCount | None = None
    notice_texts: list[IncidentNoticeInput] = Field(
        default_factory=list[IncidentNoticeInput], max_length=10
    )

    @model_validator(mode="after")
    def require_a_complete_breach_notice(self) -> Self:
        languages: list[str] = [str(text.language) for text in self.notice_texts]
        if len(set(languages)) != len(languages):
            raise ValueError("Each notice language may appear only once.")

        if len(set(self.affected_business_ids)) != len(self.affected_business_ids):
            raise ValueError("Each affected business may appear only once.")

        if self.kind is not IncidentKind.DATA_BREACH:
            if self.notice_texts:
                raise ValueError("Only a data breach carries a notice to owners.")
            return self

        if NOTICE_FALLBACK_LANGUAGE not in languages:
            raise ValueError("A breach notice needs its English texts.")

        if (
            self.approximate_subject_count is None
            or self.approximate_record_count is None
        ):
            raise ValueError(
                "A breach notice needs the approximate numbers of people and "
                "records concerned."
            )

        return self


class CreateIncidentCommand(ImmutableDTO):
    user_id: UserId
    body: CreateIncidentBody
    client_ip_address: ClientIpAddress | None = None


class IncidentView(ImmutableDTO):
    """One incident of the log, as the platform admin sees it."""

    id: IncidentId
    kind: IncidentKind
    severity: IncidentSeverity
    status: IncidentStatus
    title: IncidentTitle
    started_at: Microseconds
    detected_at: Microseconds
    affected_business_ids: list[BusinessId]
    approximate_subject_count: AffectedSubjectCount | None = None
    approximate_record_count: AffectedRecordCount | None = None
    notice_languages: list[LanguageTag]
    notified_owner_count: NotifiedOwnerCount
    notified_at: Microseconds | None = None
    reported_by: UserId
    created_at: Microseconds


class IncidentsQuery(ImmutableDTO):
    """GET /v1/admin/incidents: one page of the log, newest first."""

    user_id: UserId
    page: PageRequest


class IncidentPage(ImmutableDTO):
    items: list[IncidentView]
    next_cursor: PageCursor | None = None
