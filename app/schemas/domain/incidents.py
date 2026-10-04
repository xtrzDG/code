from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.incidents import (
    IncidentKind,
    IncidentSeverity,
    IncidentStatus,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
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
from app.schemas.typings.users.prefixed_id import UserId


class IncidentNoticeText(PersistentDocument):
    """
    The texts of a breach notice in one language (DPA section 12.1): the
    nature of the breach, the categories of people and records concerned,
    the likely consequences and the measures taken or proposed. An owner
    reads the version in their cabinet language, else the English one.
    """

    language: LanguageTag
    nature: BreachNatureText
    subject_categories: SubjectCategoriesText
    record_categories: RecordCategoriesText
    likely_consequences: LikelyConsequencesText
    measures: BreachMeasuresText


class IncidentDocument(BaseDocument):
    """
    One incident the platform team recorded (a platform collection):
    what happened, how bad, since when, which businesses it affected and
    who reported it (docs/operations/incident.md).

    A data breach carries its notice (`notice_texts`, English always, and
    the approximate numbers of people and records concerned): the owners
    of every affected business got it through the outbox when the incident
    was recorded (`notified_owner_count`, `notified_at`), and each affected
    business's audit log names the incident. `detected_at` is when the
    platform became aware of it, the start of the DPA's 48 hours.
    """

    id: IncidentId = Field(default_factory=IncidentId)
    kind: IncidentKind
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.OPEN
    title: IncidentTitle
    started_at: Microseconds
    detected_at: Microseconds
    affected_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
    approximate_subject_count: AffectedSubjectCount | None = None
    approximate_record_count: AffectedRecordCount | None = None
    notice_texts: list[IncidentNoticeText] = Field(
        default_factory=list[IncidentNoticeText]
    )
    notified_owner_count: NotifiedOwnerCount = NotifiedOwnerCount(0)
    notified_at: Microseconds | None = None
    reported_by: UserId
