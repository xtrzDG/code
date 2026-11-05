from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.niches import NicheTextReleaseKind
from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextReleaseDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.niche_texts.niche_text_commands import NicheTextCommand
from app.schemas.dto.niche_texts.niche_text_views import NicheTextReleaseView
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.admin.niche_texts.niche_text_editing import (
    NicheTextSources,
    authorize_editor,
    is_unpublished,
)
from app.use_cases.admin.niche_texts.niche_text_releases import (
    NicheTextPublication,
    publish_release,
)
from app.use_cases.admin.niche_texts.niche_text_views import release_view
from app.utilities.niches.niche_text_checks import still_valid_entries

NOTHING_TO_PUBLISH: str = (
    "The niche has no draft that differs from the version in force."
)


class PublishNicheTextsUseCase(UseCaseContract[NicheTextCommand, NicheTextReleaseView]):
    """
    POST /v1/admin/niche-templates/{niche_key}/publish: the draft becomes
    the niche's next version. From then on the tunnel and the profile
    wizard of every owner who opens them read its texts; profiles saved
    before keep theirs, and no assistant's prompt changes. Needs a fresh
    confirmation (step-up); the platform's audit log names the admin, the
    niche and the version.

    Raises:
        ConflictError: no draft, or one equal to the version in force; or
            another admin published the same version a moment ago.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        sources: NicheTextSources,
        audit_log_repo: AuditLogRepoContract,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._sources: NicheTextSources = sources
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: NicheTextCommand) -> NicheTextReleaseView:
        admin: UserDocument = authorize_editor(
            self._authorize_platform_admin, input_data.user_id
        )
        self._step_up.require_recent_authentication()
        niche_key = input_data.niche_key
        current: NicheTextReleaseDocument | None = self._sources.latest(niche_key)
        draft: NicheTextDraftDocument | None = self._sources.niche_text_repo.get_draft(
            niche_key
        )
        if draft is None or not is_unpublished(draft, current):
            raise ConflictError(NOTHING_TO_PUBLISH)

        release: NicheTextReleaseDocument = publish_release(
            self._sources.niche_text_repo,
            self._audit_log_repo,
            current,
            NicheTextPublication(
                niche_key=niche_key,
                kind=NicheTextReleaseKind.PUBLISH,
                entries=still_valid_entries(
                    self._sources.catalog(niche_key), draft.entries
                ),
                admin_id=admin.id,
                client_ip_address=input_data.client_ip_address,
                now=self._wall_clock.now_unix(),
            ),
        )
        return release_view(release, admin.display_name)
