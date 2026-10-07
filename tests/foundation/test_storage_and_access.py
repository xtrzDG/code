import pytest
from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.containers.app import AppContainer
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import ContactRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.foundation.access_support import ACCESS_SETTINGS, platform_admin
from tests.foundation.builders import build_business
from tests.foundation.support_access_builders import build_authorize_business_access

FIXED_NANOSECONDS: int = 1_790_000_000_000_000_000


def build_access_use_case() -> tuple[
    AuthorizeBusinessAccessUseCase,
    BusinessRepository,
    UserRepository,
    AuditLogRepository,
]:
    business_repo = BusinessRepository(
        InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
    )
    user_repo = UserRepository(
        InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
    )
    audit_log_repo = AuditLogRepository(
        InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](AuditLogEntryDocument)
    )
    use_case = build_authorize_business_access(
        business_repo=business_repo,
        user_repo=user_repo,
        audit_log_repo=audit_log_repo,
        wall_clock=WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: FIXED_NANOSECONDS,
        ),
        session_assurance=SessionAssuranceContext(),
        app_settings=ACCESS_SETTINGS,
    )
    return use_case, business_repo, user_repo, audit_log_repo


def test_collection_returns_independent_copies() -> None:
    _, business_repo, _, _ = build_access_use_case()
    business = build_business(UserId())
    business_repo.save(business)

    loaded = business_repo.get(business.id)
    assert loaded is not None
    loaded.name = BusinessName("Changed without save")

    reloaded = business_repo.get(business.id)
    assert reloaded is not None
    assert reloaded.name == "Trattoria Milano"


def test_owner_staff_stranger_and_platform_admin_access() -> None:
    use_case, business_repo, user_repo, audit_log_repo = build_access_use_case()
    owner_id, staff_id = UserId(), UserId()
    business = build_business(owner_id, staff_ids=[staff_id])
    business_repo.save(business)
    admin = platform_admin("ru")
    user_repo.save(admin)
    operator = PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))

    assert (
        operator.operate(
            BusinessAccessRequest(
                user_id=owner_id,
                business_id=business.id,
                required_role=BusinessMemberRole.OWNER,
            )
        ).id
        == business.id
    )
    assert (
        operator.operate(
            BusinessAccessRequest(user_id=staff_id, business_id=business.id)
        ).id
        == business.id
    )

    with pytest.raises(AccessDeniedError):
        operator.operate(
            BusinessAccessRequest(
                user_id=staff_id,
                business_id=business.id,
                required_role=BusinessMemberRole.OWNER,
            )
        )

    with pytest.raises(NotFoundError):
        operator.operate(
            BusinessAccessRequest(user_id=UserId(), business_id=business.id)
        )

    # A platform admin without an open look into the cabinet gets nothing
    # (support access: tests/users/access).
    with pytest.raises(AccessDeniedError, match="reason first"):
        operator.operate(
            BusinessAccessRequest(user_id=admin.id, business_id=business.id)
        )
    assert audit_log_repo.list_by_business(business.id) == []


def test_tenant_scoped_repository_hides_other_businesses_documents() -> None:
    contact_repo = ContactRepository(
        InMemoryDocumentCollectionAdapter[ContactDocument](ContactDocument)
    )
    first_business = build_business(UserId())
    second_business = build_business(UserId())
    contact = ContactDocument(
        business_id=first_business.id,
        phone_number=E164PhoneNumber("+995555123456"),
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.TELEGRAM,
                channel_user_id=ChannelUserId("4242"),
            )
        ],
    )
    contact_repo.save(contact)

    assert contact_repo.get(first_business.id, contact.id) is not None
    assert contact_repo.get(second_business.id, contact.id) is None
    assert (
        contact_repo.find_by_channel_identity(
            first_business.id,
            ChannelKind.TELEGRAM,
            ChannelUserId("4242"),
        )
        is not None
    )
    assert (
        contact_repo.find_by_phone_number(
            second_business.id,
            E164PhoneNumber("+995555123456"),
        )
        is None
    )
    contact_repo.delete(second_business.id, contact.id)
    assert contact_repo.get(first_business.id, contact.id) is not None


def test_app_container_wires_repositories_as_singletons() -> None:
    app_container = AppContainer()

    assert app_container.repositories.business_repo() is (
        app_container.repositories.business_repo()
    )
    assert app_container.repositories.audit_log_repo() is (
        app_container.repositories.audit_log_repo()
    )
