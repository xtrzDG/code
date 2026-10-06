from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.incidents import (
    CreateIncidentCommand,
    IncidentView,
    LinkIncidentAnnouncementCommand,
)
from app.schemas.dto.platform_announcements import (
    AnnouncementAdminView,
    CreateAnnouncementCommand,
)


class RecordIncidentOrchestrator(
    OrchestratorContract[CreateIncidentCommand, IncidentView]
):
    """
    POST /v1/admin/incidents: the incident is recorded (and its businesses
    told, or their walk queued) first, so the log holds it whatever
    follows; when the admin also wrote the matching status announcement
    it is published next (the cabinet's banner and /status, with its own
    checks and audit entry) and linked to the incident. A refused
    announcement fails the request after the incident was recorded: the
    admin publishes it from the announcements page instead.
    """

    def __init__(
        self,
        create_incident: UseCaseContract[CreateIncidentCommand, IncidentView],
        create_announcement: UseCaseContract[
            CreateAnnouncementCommand, AnnouncementAdminView
        ],
        link_announcement: UseCaseContract[
            LinkIncidentAnnouncementCommand, IncidentView
        ],
    ) -> None:
        self._create_incident: UseCaseContract[CreateIncidentCommand, IncidentView] = (
            create_incident
        )
        self._create_announcement: UseCaseContract[
            CreateAnnouncementCommand, AnnouncementAdminView
        ] = create_announcement
        self._link_announcement: UseCaseContract[
            LinkIncidentAnnouncementCommand, IncidentView
        ] = link_announcement

    def execute(self, input_data: CreateIncidentCommand) -> IncidentView:
        incident: IncidentView = self._create_incident.run(input_data)
        announcement_body = input_data.body.announcement
        if announcement_body is None:
            return incident

        announcement: AnnouncementAdminView = self._create_announcement.run(
            CreateAnnouncementCommand(
                user_id=input_data.user_id,
                body=announcement_body,
                client_ip_address=input_data.client_ip_address,
            )
        )
        return self._link_announcement.run(
            LinkIncidentAnnouncementCommand(
                incident_id=incident.id, announcement_id=announcement.id
            )
        )
