"""
The niche template editor in memory: the code's real templates and starter
answers, the drafts and versions, the audit log, the admins and a clock the
tests move; the use cases built over them like the typed root builds them.
"""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.niches.effective_niche_template_registry import (
    EffectiveNicheTemplateRegistry,
)
from app.registries.niches.effective_starter_answer_registry import (
    EffectiveStarterAnswerRegistry,
)
from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.registries.niches.starter_answer_registry import StarterAnswerRegistry
from app.repositories.niche_text_repository import NicheTextRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextReleaseDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.niche_texts.niche_text_commands import (
    NicheTextCommand,
    NicheTextEditorQuery,
    NicheTextInput,
    RevertNicheTextsCommand,
    SaveNicheTextDraftCommand,
)
from app.schemas.dto.niche_texts.niche_text_views import (
    NicheTextEditorView,
    NicheTextReleaseView,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.niches.constrained_integers import NicheTextVersion
from app.schemas.typings.niches.constrained_strings import (
    NicheOverrideText,
    NicheTextFieldKey,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import UserDisplayName
from app.use_cases.admin.niche_texts.discard_niche_text_draft_use_case import (
    DiscardNicheTextDraftUseCase,
)
from app.use_cases.admin.niche_texts.get_niche_text_editor_use_case import (
    GetNicheTextEditorUseCase,
)
from app.use_cases.admin.niche_texts.list_niche_text_versions_use_case import (
    ListNicheTextVersionsUseCase,
)
from app.use_cases.admin.niche_texts.list_niche_texts_use_case import (
    ListNicheTextsUseCase,
)
from app.use_cases.admin.niche_texts.niche_text_editing import NicheTextSources
from app.use_cases.admin.niche_texts.publish_niche_texts_use_case import (
    PublishNicheTextsUseCase,
)
from app.use_cases.admin.niche_texts.revert_niche_texts_use_case import (
    RevertNicheTextsUseCase,
)
from app.use_cases.admin.niche_texts.save_niche_text_draft_use_case import (
    SaveNicheTextDraftUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.compliance.audit_repositories import audit_log_repository
from tests.platform_ops.incident_world import StepUp
from tests.platform_ops.ops_world import ADMIN, AdminsOnly, OpsClock

IP: ClientIpAddress = ClientIpAddress("203.0.113.9")
IT: LanguageTag = LanguageTag("it")
EN: LanguageTag = LanguageTag("en")
RESTAURANT: NicheKey = NicheKey.RESTAURANT
CUISINE_LABEL: NicheTextFieldKey = NicheTextFieldKey("questions.cuisine.label")


def texts(**fields: str) -> list[NicheTextInput]:
    """Inputs by field key, dots written as double underscores."""

    return [
        NicheTextInput(
            field_key=NicheTextFieldKey(key.replace("__", ".")),
            text=NicheOverrideText(text),
        )
        for key, text in fields.items()
    ]


class NicheTextWorld:
    def __init__(self, is_recent: bool = True) -> None:
        self.clock = OpsClock()
        self.drafts = InMemoryDocumentCollectionAdapter[NicheTextDraftDocument](
            NicheTextDraftDocument
        )
        self.releases = InMemoryDocumentCollectionAdapter[NicheTextReleaseDocument](
            NicheTextReleaseDocument
        )
        self.audit = InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
            AuditLogEntryDocument
        )
        self.users = InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
        self.repo = NicheTextRepository(self.drafts, self.releases)
        self.user_repo = UserRepository(self.users)
        self.audit_repo = audit_log_repository(self.audit)
        self.code_templates = NicheTemplateRegistry()
        self.code_starters = StarterAnswerRegistry()
        self.effective_templates = EffectiveNicheTemplateRegistry(
            self.code_templates, self.repo
        )
        self.effective_starters = EffectiveStarterAnswerRegistry(
            self.code_starters, self.repo
        )
        self.sources = NicheTextSources(
            niche_templates=self.code_templates,
            starter_answers=self.code_starters,
            niche_text_repo=self.repo,
        )
        self.step_up = StepUp(is_recent)
        self.resolver = LocalizedTextResolver()
        self.user_repo.save(
            UserDocument(
                id=ADMIN,
                login_method=LoginMethod.EMAIL,
                email=EmailAddress("nino@workshop.example"),
                locale=EN,
                display_name=UserDisplayName("Nino Admin"),
            )
        )

    @property
    def admin_name(self) -> UserDisplayName:
        return UserDisplayName("Nino Admin")

    def list_use_case(self) -> ListNicheTextsUseCase:
        return ListNicheTextsUseCase(
            AdminsOnly(), self.sources, self.user_repo, self.resolver
        )

    def editor_use_case(self) -> GetNicheTextEditorUseCase:
        return GetNicheTextEditorUseCase(
            AdminsOnly(), self.sources, self.user_repo, self.resolver
        )

    def save_use_case(self) -> SaveNicheTextDraftUseCase:
        return SaveNicheTextDraftUseCase(
            AdminsOnly(),
            self.sources,
            self.user_repo,
            self.resolver,
            self.clock.wall_clock,
        )

    def publish_use_case(self) -> PublishNicheTextsUseCase:
        return PublishNicheTextsUseCase(
            AdminsOnly(),
            self.sources,
            self.audit_repo,
            self.step_up,
            self.clock.wall_clock,
        )

    def revert_use_case(self) -> RevertNicheTextsUseCase:
        return RevertNicheTextsUseCase(
            AdminsOnly(),
            self.sources,
            self.audit_repo,
            self.step_up,
            self.clock.wall_clock,
        )

    def discard_use_case(self) -> DiscardNicheTextDraftUseCase:
        return DiscardNicheTextDraftUseCase(AdminsOnly(), self.repo)

    def history_use_case(self) -> ListNicheTextVersionsUseCase:
        return ListNicheTextVersionsUseCase(AdminsOnly(), self.repo, self.user_repo)

    # --- Steps as an admin takes them.
    def editor(
        self, niche: NicheKey = RESTAURANT, language: LanguageTag = IT
    ) -> NicheTextEditorView:
        return self.editor_use_case().run(
            NicheTextEditorQuery(user_id=ADMIN, niche_key=niche, language=language)
        )

    def save(
        self,
        language: LanguageTag,
        **fields: str,
    ) -> NicheTextEditorView:
        return self.save_use_case().run(
            SaveNicheTextDraftCommand(
                user_id=ADMIN,
                niche_key=RESTAURANT,
                language=language,
                texts=texts(**fields),
            )
        )

    def publish(self, niche: NicheKey = RESTAURANT) -> NicheTextReleaseView:
        self.clock.advance(60_000_000)
        return self.publish_use_case().run(
            NicheTextCommand(user_id=ADMIN, niche_key=niche, client_ip_address=IP)
        )

    def revert(
        self, version: int, niche: NicheKey = RESTAURANT
    ) -> NicheTextReleaseView:
        self.clock.advance(60_000_000)
        return self.revert_use_case().run(
            RevertNicheTextsCommand(
                user_id=ADMIN,
                niche_key=niche,
                version=NicheTextVersion(version),
                client_ip_address=IP,
            )
        )

    def audit_entries(self) -> list[AuditLogEntryDocument]:
        return sorted(self.audit.list_all(), key=lambda entry: entry.created_at)

    def now(self) -> Microseconds:
        return Microseconds(self.clock.now)
