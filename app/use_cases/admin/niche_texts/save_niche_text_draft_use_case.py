from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextEntry,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.niche_texts.niche_text_commands import SaveNicheTextDraftCommand
from app.schemas.dto.niche_texts.niche_text_fields import NicheTextCatalog
from app.schemas.dto.niche_texts.niche_text_views import NicheTextEditorView
from app.use_cases.admin.niche_texts.niche_text_editing import (
    NicheTextSources,
    authorize_editor,
    ordered_entries,
    published_entries,
    same_entries,
)
from app.use_cases.admin.niche_texts.niche_text_views import load_editor_view
from app.utilities.niches.niche_text_checks import check_draft_texts


class SaveNicheTextDraftUseCase(
    UseCaseContract[SaveNicheTextDraftCommand, NicheTextEditorView]
):
    """
    PUT /v1/admin/niche-templates/{niche_key}/draft: the admin's texts of
    one language replace that language's texts of the niche's draft (the
    first save starts the draft from the version in force; a field left out
    keeps the code's wording). Owners read nothing of it until it is
    published; a draft that comes back to the version in force is dropped.
    Answers the editor in that language.

    Raises:
        ValidationFailedError: an unknown field, a language the cabinet
            does not speak, a text too long for its field or without the
            code text's placeholders.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        sources: NicheTextSources,
        user_repo: UserRepoContract,
        localized_text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._sources: NicheTextSources = sources
        self._user_repo: UserRepoContract = user_repo
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SaveNicheTextDraftCommand) -> NicheTextEditorView:
        admin: UserDocument = authorize_editor(
            self._authorize_platform_admin, input_data.user_id
        )
        niche_key = input_data.niche_key
        catalog: NicheTextCatalog = self._sources.catalog(niche_key)
        written: list[NicheTextEntry] = check_draft_texts(
            catalog, input_data.language, input_data.texts
        )
        repo = self._sources.niche_text_repo
        published: list[NicheTextEntry] = published_entries(
            self._sources.latest(niche_key)
        )
        draft: NicheTextDraftDocument | None = repo.get_draft(niche_key)
        starting: list[NicheTextEntry] = published if draft is None else draft.entries
        entries: list[NicheTextEntry] = ordered_entries(
            catalog,
            [
                *(entry for entry in starting if entry.language != input_data.language),
                *written,
            ],
        )
        if same_entries(entries, published):
            repo.delete_draft(niche_key)
        else:
            now: Microseconds = self._wall_clock.now_unix()
            repo.save_draft(
                NicheTextDraftDocument(
                    niche_key=niche_key,
                    entries=entries,
                    updated_by=admin.id,
                    created_at=now if draft is None else draft.created_at,
                    updated_at=now,
                )
            )

        return load_editor_view(
            self._sources,
            self._user_repo,
            self._resolver,
            niche_key,
            input_data.language,
        )
