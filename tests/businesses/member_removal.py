"""
RemoveMemberUseCase over in-memory API keys and webhooks, for the team
tests that build the use case by hand (the keys a removed member made are
revoked with them).
"""

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.webhook_repositories import WebhookEndpointRepository
from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.domain.webhooks import WebhookEndpointDocument
from app.use_cases.businesses.member_mutation_guard import MemberMutationGuard
from app.use_cases.businesses.remove_member_use_case import RemoveMemberUseCase


def build_remove_member(
    member_mutations: MemberMutationGuard,
    audit_log_repo: AuditLogRepoContract,
    wall_clock: WallClock[Microseconds],
    api_key_repo: ApiKeyRepository | None = None,
) -> RemoveMemberUseCase:
    return RemoveMemberUseCase(
        member_mutations=member_mutations,
        api_key_repo=api_key_repo
        or ApiKeyRepository(InMemoryDocumentCollectionAdapter(ApiKeyDocument)),
        endpoint_repo=WebhookEndpointRepository(
            InMemoryDocumentCollectionAdapter(WebhookEndpointDocument)
        ),
        audit_log_repo=audit_log_repo,
        wall_clock=wall_clock,
    )
