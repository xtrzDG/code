from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.privacy import CsvExportKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.privacy.csv_exports import CsvExportHeader, StartCsvExportCommand
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.privacy.constrained_strings import ExportFileName
from app.schemas.typings.privacy.strings import CsvColumnTitle
from app.utilities.privacy.csv_columns import CSV_COLUMNS
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000
# The audit log names an export by the records it copies.
EXPORTED_ENTITY: dict[CsvExportKind, AuditEntityName] = {
    CsvExportKind.BOOKINGS: AuditEntityName("booking"),
    CsvExportKind.LEADS: AuditEntityName("lead"),
    CsvExportKind.CONTACTS: AuditEntityName("contact"),
    CsvExportKind.CONVERSATIONS: AuditEntityName("conversation"),
    CsvExportKind.AUDIT_LOG: AuditEntityName("audit_log"),
}
CSV_REFERENCE: AuditEntityReference = AuditEntityReference("csv")


class StartCsvExportUseCase(UseCaseContract[StartCsvExportCommand, CsvExportHeader]):
    """
    The owner downloads a table of the cabinet (bookings, leads, customers,
    conversations with their messages, the audit log) as CSV.

    Personal data leaves the platform, so only an owner may (never staff,
    never read-only platform support), only after a recent sign-in or
    step-up, and the export is written to the audit log once (EXPORT of the
    records' type, reference "csv") before any row is read. Returns the file
    name (the table and the business's local date) and the headings in the
    owner's language; the rows follow a page at a time
    (ReadCsvExportPageUseCase).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
        text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._step_up: StepUpGuardContract = step_up
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def run(self, input_data: StartCsvExportCommand) -> CsvExportHeader:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
                access_mode=BusinessAccessMode.WRITE,
            )
        )
        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.EXPORT,
                entity=EXPORTED_ENTITY[input_data.kind],
                entity_id=CSV_REFERENCE,
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return CsvExportHeader(
            file_name=export_file_name(
                input_data.kind, now, load_time_zone(business.timezone)
            ),
            columns=[
                CsvColumnTitle(
                    str(self._text_resolver.resolve(title, input_data.language))
                )
                for title in CSV_COLUMNS[input_data.kind]
            ],
        )


def export_file_name(
    kind: CsvExportKind, now: Microseconds, zone: ZoneInfo
) -> ExportFileName:
    """ "bookings-2026-10-04.csv": the table and the business's local date."""

    local_day: str = (
        datetime.fromtimestamp(int(now) / MICROSECONDS_PER_SECOND, tz=UTC)
        .astimezone(zone)
        .date()
        .isoformat()
    )
    return ExportFileName(f"{kind.value.replace('_', '-')}-{local_day}.csv")
