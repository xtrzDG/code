"""
The incident use cases wired in memory: owners in two languages, staff, two
businesses, a recording notifier, the outbox-free job queue, the status
page's announcements and a clock the tests move.
"""

import json

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.platform_announcement_repository import (
    PlatformAnnouncementRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.domain.platform_status import PlatformAnnouncementDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.incidents import CreateIncidentBody, CreateIncidentCommand
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.businesses.constrained_integers import BusinessBatchSize
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.admin.incidents.create_incident_use_case import (
    CreateIncidentUseCase,
)
from app.use_cases.admin.incidents.expand_incident_use_case import (
    ExpandIncidentUseCase,
)
from app.use_cases.admin.incidents.incident_reach import IncidentReach
from app.use_cases.admin.incidents.owner_breach_notices import OwnerBreachNotices
from tests.channels.outbox_fakes import RecordingUnitOfWork
from tests.knowledge.website_import.recording_job_queue import RecordingJobQueue
from tests.platform_ops.ops_documents import HOUR, at, business, member
from tests.platform_ops.ops_world import ADMIN, AdminsOnly, OpsClock, put

RU_OWNER = UserDocument(
    login_method=LoginMethod.EMAIL,
    email=EmailAddress("nino@salon.example"),
    locale=LanguageTag("ru"),
)
KA_OWNER = UserDocument(
    login_method=LoginMethod.PHONE,
    phone_number=E164PhoneNumber("+995555123456"),
    locale=LanguageTag("ka"),
)
STAFF = UserDocument(
    login_method=LoginMethod.EMAIL,
    email=EmailAddress("giorgi@salon.example"),
    locale=LanguageTag("en"),
)
OTHER_OWNER = UserDocument(
    login_method=LoginMethod.EMAIL,
    email=EmailAddress("owner@cafe.example"),
    locale=LanguageTag("en"),
)


class RecordingNotifier:
    def __init__(self) -> None:
        self.sent: list[StaffNotification] = []

    def notify(self, notification: StaffNotification) -> bool:
        self.sent.append(notification)
        return True


class StepUp(StepUpGuardContract):
    def __init__(self, is_recent: bool) -> None:
        self._is_recent: bool = is_recent

    def require_recent_authentication(self) -> None:
        if not self._is_recent:
            raise StepUpRequiredError("Sign in again first.")


class IncidentWorld:
    def __init__(self, is_recent: bool = True) -> None:
        self.clock = OpsClock()
        self.users = InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
        self.businesses = InMemoryDocumentCollectionAdapter[BusinessDocument](
            BusinessDocument
        )
        self.incidents = InMemoryDocumentCollectionAdapter[IncidentDocument](
            IncidentDocument
        )
        self.audit = InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
            AuditLogEntryDocument
        )
        self.notifier = RecordingNotifier()
        put(self.users, RU_OWNER, KA_OWNER, STAFF, OTHER_OWNER)
        self.salon = business(
            "Salon Ia",
            member(RU_OWNER.id, BusinessMemberRole.OWNER),
            member(KA_OWNER.id, BusinessMemberRole.OWNER),
            member(STAFF.id, BusinessMemberRole.STAFF),
        )
        self.cafe = business("Café", member(OTHER_OWNER.id, BusinessMemberRole.OWNER))
        put(self.businesses, self.salon, self.cafe)
        self.announcements = InMemoryDocumentCollectionAdapter[
            PlatformAnnouncementDocument
        ](PlatformAnnouncementDocument)
        self.queue = RecordingJobQueue()
        self.transactions = RecordingUnitOfWork()
        self.business_repo = BusinessRepository(self.businesses)
        self.incident_repo = IncidentRepository(self.incidents)
        self.audit_repo = AuditLogRepository(self.audit)
        self.announcement_repo = PlatformAnnouncementRepository(self.announcements)
        self.reach = IncidentReach(
            OwnerBreachNotices(UserRepository(self.users), self.notifier),
            self.audit_repo,
        )
        self.step_up = StepUp(is_recent)
        self.use_case = CreateIncidentUseCase(
            authorize_platform_admin=AdminsOnly(),
            business_repo=self.business_repo,
            incident_repo=self.incident_repo,
            reach=self.reach,
            job_queue=self.queue,
            unit_of_work=self.transactions,
            step_up=self.step_up,
            wall_clock=self.clock.wall_clock,
        )

    def expansion(self, batch_size: int = 200) -> ExpandIncidentUseCase:
        return ExpandIncidentUseCase(
            incident_repo=self.incident_repo,
            business_repo=self.business_repo,
            reach=self.reach,
            job_queue=self.queue,
            unit_of_work=self.transactions,
            wall_clock=self.clock.wall_clock,
            batch_size=BusinessBatchSize(batch_size),
        )


def breach(*businesses: BusinessDocument, **changes: object) -> CreateIncidentCommand:
    texts = {
        "subject_categories": "Customers",
        "record_categories": "Names and phone numbers",
        "likely_consequences": "Unwanted calls.",
        "measures": "The file was deleted.",
    }
    body: dict[str, object] = {
        "kind": "data_breach",
        "severity": "sev1",
        "title": "Customer export sent to the wrong address",
        "started_at": int(at(-2 * HOUR)),
        "affected_business_ids": [str(item.id) for item in businesses],
        "approximate_subject_count": 40,
        "approximate_record_count": 80,
        "notice_texts": [
            {"language": "en", "nature": "An export was e-mailed wrongly.", **texts},
            {"language": "ka", "nature": "ექსპორტი შეცდომით გაიგზავნა.", **texts},
        ],
        **changes,
    }
    return CreateIncidentCommand(
        user_id=ADMIN, body=CreateIncidentBody.model_validate_json(json.dumps(body))
    )
