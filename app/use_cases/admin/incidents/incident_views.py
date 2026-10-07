from app.schemas.constants.incidents import IncidentScope
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.dto.incidents import IncidentView
from app.schemas.typings.incidents.constrained_integers import AffectedBusinessCount


def incident_view(incident: IncidentDocument) -> IncidentView:
    """The incident as the admin pages show it (the notice texts by language only)."""

    is_all: bool = incident.scope is IncidentScope.ALL_BUSINESSES
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
        scope=incident.scope,
        affected_business_count=(
            incident.reached_business_count or AffectedBusinessCount(0)
            if is_all
            else AffectedBusinessCount(len(incident.affected_business_ids))
        ),
        is_expanding=is_all and incident.expanded_at is None,
        announcement_id=incident.announcement_id,
    )
