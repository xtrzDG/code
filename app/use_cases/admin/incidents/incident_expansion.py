"""
The `expand_incident` job of an incident that affected every business:
one keyset batch of businesses per run, the next run queued by the last
(`ExpandIncidentUseCase`), one run at a time per incident.
"""

from app.schemas.dto.incidents import IncidentExpansionPayload
from app.schemas.typings.businesses.constrained_integers import BusinessBatchSize
from app.schemas.typings.incidents.prefixed_id import IncidentId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson

EXPAND_INCIDENT_JOB: JobName = JobName("expand_incident")
# Each batch's notices, audit entries and progress commit together.
INCIDENT_BATCH_SIZE: BusinessBatchSize = BusinessBatchSize(200)


def expansion_serial_key(incident_id: IncidentId) -> JobSerialKey:
    """The runs of one incident's walk never overlap."""

    return JobSerialKey(f"incident:{incident_id}")


def expansion_payload(incident_id: IncidentId) -> JobPayloadJson:
    return JobPayloadJson(
        IncidentExpansionPayload(incident_id=incident_id).model_dump_json()
    )
