from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.niche_text_repositories import NicheTextRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.contracts.starter_registries import StarterAnswerRegistryContract
from app.contracts.storage import StorageScopeContract


@dataclass(frozen=True, slots=True, kw_only=True)
class NicheTextDependencies:
    """
    Everything the platform admin's niche template editor
    (R17-NICHE-TEMPLATE-EDITOR, migration 1221) takes from the rest of the
    application, as contracts: the code's templates and starter answers
    (never the effective ones: the editor shows the code's wording beside
    the overrides), the drafts and versions, the admin check's parts, the
    audit log and the step-up guard. The only place the dependency graph
    meets the typed root (app/containers/use_cases/niche_text_root_provider.py
    fills it).
    """

    niche_templates: NicheTemplateRegistryContract
    starter_answers: StarterAnswerRegistryContract
    niche_text_repo: NicheTextRepoContract
    user_repo: UserRepoContract
    audit_log_repo: AuditLogRepoContract
    session_assurance: SessionAssuranceContract
    platform_admins: PlatformAdminRegistryContract
    step_up: StepUpGuardContract
    localized_text_resolver: LocalizedTextResolverContract
    storage_scope: StorageScopeContract
    wall_clock: WallClock[Microseconds]
