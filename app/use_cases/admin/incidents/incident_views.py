from app.schemas.domain.incidents import IncidentDocument
from app.schemas.dto.incidents import IncidentView


def incident_view(incident: IncidentDocument) -> IncidentView:
    """The incident as the admin pages show it (the notice texts by language only)."""

    return IncidentView(
        id=incident.id,
        kind=incident.kind,
        severity=incident.severity,
        status=incident.status,
        title=incident.title,
        started_at=incident.started_at,
        detected_at=incident.detected_at,
        affected_business_ids=list(incident.affected_business_ids),
        approximate_subject_count=incident.approximate_subject_count,
        approximate_record_count=incident.approximate_record_count,
        notice_languages=[text.language for text in incident.notice_texts],
        notified_owner_count=incident.notified_owner_count,
        notified_at=incident.notified_at,
        reported_by=incident.reported_by,
        created_at=incident.created_at,
    )
