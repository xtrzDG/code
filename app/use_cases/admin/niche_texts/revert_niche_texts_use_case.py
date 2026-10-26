from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.niches import NicheTextReleaseKind
from app.schemas.domain.niche_texts import NicheTextEntry, NicheTextReleaseDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.niche_texts.niche_text_commands import RevertNicheTextsCommand
from app.schemas.dto.niche_texts.niche_text_views import NicheTextReleaseView
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.use_cases.admin.niche_texts.niche_text_editing import NicheTextSources
from app.use_cases.admin.niche_texts.niche_text_releases import (
    NicheTextPublication,
    publish_release,
)
from app.use_cases.admin.niche_texts.niche_text_views import release_view
from app.utilities.niches.niche_text_checks import still_valid_entries


class RevertNicheTextsUseCase(
    UseCaseContract[RevertNicheTextsCommand, NicheTextReleaseView]
):
    """
    POST /v1/admin/niche-templates/{niche_key}/revert {version}: publish
    again the texts of an earlier version (REVERT), or of version 0, the
    code template's own wording (RESET), as the niche's next version; the
    history keeps every version. A text the code no longer accepts (a field
    it dropped) is left out. Removes the draft. Step-up and audit like
    publishing.

    Raises:
        NotFoundError: the niche has no such version.
        ConflictError: that version's texts are in force already; or
            another admin published a moment ago.
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

    def run(self, input_data: RevertNicheTextsCommand) -> NicheTextReleaseView:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_NICHE_TEMPLATES,
            )
        )
        self._step_up.require_recent_authentication()
        niche_key = input_data.niche_key
        target = int(input_data.version)
        current: NicheTextReleaseDocument | None = self._sources.latest(niche_key)
        if target == (0 if current is None else int(current.version)):
            raise ConflictError(f"Version {target} is in force already.")

        entries: list[NicheTextEntry] = []
        if target > 0:
            restored: NicheTextReleaseDocument | None = (
                self._sources.niche_text_repo.get_release(niche_key, input_data.version)
            )
            if restored is None:
                raise NotFoundError(f"The niche has no version {target}.")

            entries = still_valid_entries(
                self._sources.catalog(niche_key), restored.entries
            )

        release: NicheTextReleaseDocument = publish_release(
            self._sources.niche_text_repo,
            self._audit_log_repo,
            current,
            NicheTextPublication(
                niche_key=niche_key,
                kind=(
                    NicheTextReleaseKind.REVERT
                    if target > 0
                    else NicheTextReleaseKind.RESET
                ),
                entries=entries,
                restored_version=input_data.version if target > 0 else None,
                admin_id=admin.id,
                client_ip_address=input_data.client_ip_address,
                now=self._wall_clock.now_unix(),
            ),
        )
        return release_view(release, admin.display_name)
