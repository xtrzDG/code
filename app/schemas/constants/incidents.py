from enum import StrEnum


class IncidentSeverity(StrEnum):
    """
    How bad an incident is (docs/operations/incident.md): SEV1 most or all
    customers get no answers, or personal data left the platform; SEV2 one
    channel, provider or feature is down for many, or answers are slow;
    SEV3 a few businesses are affected, or there is a workaround.
    """

    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"


class IncidentKind(StrEnum):
    """
    What happened: an outage (customers get no answers), degraded service
    (slow or partial answers), or a personal data breach, which the
    affected owners are told about under section 12.1 of the DPA.
    """

    OUTAGE = "outage"
    DEGRADATION = "degradation"
    DATA_BREACH = "data_breach"


class IncidentStatus(StrEnum):
    """Whether an incident is still being handled or over."""

    OPEN = "open"
    RESOLVED = "resolved"
