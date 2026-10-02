"""In-memory cabinet wiring for the call forwarding flow."""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.operator_contract import OperatorContract
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.localization.call_forwarding_instructions_orchestrator import (
    CallForwardingInstructionsOrchestrator,
)
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.localization.call_forwarding_guide_registry import (
    CallForwardingGuideRegistry,
)
from app.repositories.business_repositories import BusinessRepository, ChannelRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.catalog.call_forwarding import (
    CallForwardingInstructions,
    CallForwardingInstructionsRequest,
)
from app.schemas.typings.channels.strings import ChannelExternalId
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.localization.build_call_forwarding_instructions_use_case import (
    BuildCallForwardingInstructionsUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from tests.localization.builders import build_wall_clock

type CallForwardingOperator = OperatorContract[
    CallForwardingInstructionsRequest, CallForwardingInstructions
]


@dataclass(frozen=True)
class CabinetWorld:
    business_repo: BusinessRepository
    user_repo: UserRepository
    channel_repo: ChannelRepository
    audit_log_repo: AuditLogRepository
    call_forwarding_operator: CallForwardingOperator


def build_cabinet_world() -> CabinetWorld:
    business_repo = BusinessRepository(
        InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
    )
    user_repo = UserRepository(
        InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
    )
    channel_repo = ChannelRepository(
        InMemoryDocumentCollectionAdapter[ChannelDocument](ChannelDocument)
    )
    audit_log_repo = AuditLogRepository(
        InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](AuditLogEntryDocument)
    )
    orchestrator = CallForwardingInstructionsOrchestrator(
        authorize_business_access_use_case=AuthorizeBusinessAccessUseCase(
            business_repo=business_repo,
            user_repo=user_repo,
            audit_log_repo=audit_log_repo,
            wall_clock=build_wall_clock(),
        ),
        build_call_forwarding_instructions_use_case=(
            BuildCallForwardingInstructionsUseCase(
                channel_repo=channel_repo,
                phone_number_parser=PhoneNumberParser(),
                call_forwarding_guide_registry=CallForwardingGuideRegistry(),
                localized_text_resolver=LocalizedTextResolver(),
            )
        ),
    )
    return CabinetWorld(
        business_repo=business_repo,
        user_repo=user_repo,
        channel_repo=channel_repo,
        audit_log_repo=audit_log_repo,
        call_forwarding_operator=PipelineOperator(OrchestratorPipeline(orchestrator)),
    )


def add_phone_channel(
    world: CabinetWorld,
    business: BusinessDocument,
    external_id: str | None,
    status: ChannelStatus = ChannelStatus.CONNECTED,
    created_at: int = 1_790_000_000_000_000,
    kind: ChannelKind = ChannelKind.PHONE,
) -> ChannelDocument:
    channel = ChannelDocument(
        business_id=business.id,
        kind=kind,
        external_id=ChannelExternalId(external_id) if external_id is not None else None,
        status=status,
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )
    world.channel_repo.save(channel)
    return channel
