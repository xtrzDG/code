"""
POST /v1/admin/incidents' use case: an incident is stored with one audit
entry per affected business; a data breach tells every owner of those
businesses (not their staff, not other businesses) in the owner's language,
by e-mail or else SMS; the admin must have signed in recently.
"""

import json

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.incidents import CreateIncidentBody, CreateIncidentCommand
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.admin.incidents.create_incident_use_case import (
    CreateIncidentUseCase,
)
from app.use_cases.admin.incidents.owner_breach_notices import OwnerBreachNotices
from tests.platform_ops.ops_documents import DAY, HOUR, at, business, member
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
        self.use_case = CreateIncidentUseCase(
            authorize_platform_admin=AdminsOnly(),
            business_repo=BusinessRepository(self.businesses),
            incident_repo=IncidentRepository(self.incidents),
            audit_log_repo=AuditLogRepository(self.audit),
            breach_notices=OwnerBreachNotices(
                UserRepository(self.users), self.notifier
            ),
            step_up=StepUp(is_recent),
            wall_clock=self.clock.wall_clock,
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


def test_a_breach_tells_every_owner_of_the_affected_business_only() -> None:
    world = IncidentWorld()

    view = world.use_case.run(breach(world.salon))

    assert int(view.notified_owner_count) == 2 and view.notified_at is not None
    by_channel = {sent.contact.channel: sent for sent in world.notifier.sent}
    assert set(by_channel) == {ManagerContactChannel.EMAIL, ManagerContactChannel.SMS}
    email, sms = (
        by_channel[ManagerContactChannel.EMAIL],
        by_channel[ManagerContactChannel.SMS],
    )
    assert str(email.contact.address) == "nino@salon.example"
    assert str(sms.contact.address) == "+995555123456"
    assert {sent.business_id for sent in world.notifier.sent} == {world.salon.id}
    assert str(email.subject) == f"incident:{view.id}"
    # Russian has a frame but no texts of the team: the frame is Russian,
    # the texts English; Georgian has both.
    assert str(email.text).startswith("Уведомление о нарушении")
    assert "An export was e-mailed wrongly." in str(email.text)
    assert "ექსპორტი შეცდომით გაიგზავნა." in str(sms.text)
    assert "(Asia/Tbilisi)" in str(sms.text)


def test_each_affected_business_gets_an_audit_entry_naming_the_incident() -> None:
    world = IncidentWorld()

    view = world.use_case.run(breach(world.salon, world.cafe))

    entries = world.audit.list_all()
    assert sorted(str(entry.business_id) for entry in entries) == sorted(
        [str(world.salon.id), str(world.cafe.id)]
    )
    assert {str(entry.entity_id) for entry in entries} == {str(view.id)}
    assert {entry.actor_id for entry in entries} == {ADMIN}
    assert int(view.notified_owner_count) == 3
    [stored] = world.incidents.list_all()
    assert stored.affected_business_ids == [world.salon.id, world.cafe.id]


def test_an_outage_is_recorded_without_notices() -> None:
    world = IncidentWorld()
    outage = CreateIncidentCommand(
        user_id=ADMIN,
        body=CreateIncidentBody.model_validate_json(
            json.dumps(
                {
                    "kind": "outage",
                    "severity": "sev2",
                    "title": "Replies delayed",
                    "started_at": int(at(-HOUR)),
                    "affected_business_ids": [str(world.salon.id)],
                }
            )
        ),
    )

    view = world.use_case.run(outage)

    assert world.notifier.sent == []
    assert int(view.notified_owner_count) == 0 and view.notified_at is None
    assert len(world.audit.list_all()) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"started_at": int(at(HOUR))},
        {"detected_at": int(at(-3 * HOUR))},
        {"detected_at": int(at(DAY))},
    ],
)
def test_the_timeline_must_make_sense(changes: dict[str, object]) -> None:
    world = IncidentWorld()

    with pytest.raises(ValidationFailedError):
        world.use_case.run(breach(world.salon, **changes))

    assert world.incidents.list_all() == [] and world.notifier.sent == []


def test_an_unknown_business_refuses_the_whole_incident() -> None:
    world = IncidentWorld()
    gone = business("Closed")

    with pytest.raises(ValidationFailedError, match=str(gone.id)):
        world.use_case.run(breach(world.salon, gone))

    assert world.incidents.list_all() == [] and world.audit.list_all() == []


def test_a_stale_session_must_sign_in_again() -> None:
    world = IncidentWorld(is_recent=False)

    with pytest.raises(StepUpRequiredError):
        world.use_case.run(breach(world.salon))

    assert world.incidents.list_all() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"notice_texts": []},
        {"approximate_record_count": None},
        {"affected_business_ids": []},
        {"kind": "outage"},
    ],
)
def test_a_breach_body_needs_its_dpa_fields(changes: dict[str, object]) -> None:
    world = IncidentWorld()

    with pytest.raises(ValueError):
        breach(world.salon, **changes)
