from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.help import (
    HelpArticleQuery,
    HelpArticleView,
    HelpCenterQuery,
    HelpCenterView,
    HelpSearchRequest,
    HelpSearchResults,
    SupportContactsQuery,
    SupportContactsView,
)
from app.schemas.dto.help_progress import (
    ChangelogReadCommand,
    CoachMarkSeenCommand,
    HelpProgressQuery,
    HelpProgressView,
)
from app.use_cases.help.get_help_article_use_case import GetHelpArticleUseCase
from app.use_cases.help.get_help_center_use_case import GetHelpCenterUseCase
from app.use_cases.help.get_help_progress_use_case import GetHelpProgressUseCase
from app.use_cases.help.get_support_contacts_use_case import (
    GetSupportContactsUseCase,
)
from app.use_cases.help.mark_coach_mark_seen_use_case import (
    MarkCoachMarkSeenUseCase,
)
from app.use_cases.help.read_changelog_use_case import ReadChangelogUseCase
from app.use_cases.help.reset_coach_marks_use_case import ResetCoachMarksUseCase
from app.use_cases.help.search_help_use_case import SearchHelpUseCase


class HelpUseCasesContainer(containers.DeclarativeContainer):
    """
    The help center (articles, search, the platform's support contacts)
    and what each person has seen of the cabinet's guidance (coach marks,
    "What's new").
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    get_help_center_use_case: Factory[
        UseCaseContract[HelpCenterQuery, HelpCenterView]
    ] = Factory(
        GetHelpCenterUseCase,
        help_article_registry=registries.help_article_registry,
    )
    get_help_article_use_case: Factory[
        UseCaseContract[HelpArticleQuery, HelpArticleView]
    ] = Factory(
        GetHelpArticleUseCase,
        help_article_registry=registries.help_article_registry,
    )
    search_help_use_case: Factory[
        UseCaseContract[HelpSearchRequest, HelpSearchResults]
    ] = Factory(
        SearchHelpUseCase,
        help_article_registry=registries.help_article_registry,
    )
    get_support_contacts_use_case: Factory[
        UseCaseContract[SupportContactsQuery, SupportContactsView]
    ] = Factory(
        GetSupportContactsUseCase,
        support_settings=config.app_settings.provided.support,
    )
    get_help_progress_use_case: Factory[
        UseCaseContract[HelpProgressQuery, HelpProgressView]
    ] = Factory(
        GetHelpProgressUseCase,
        help_progress_repo=repositories.help_progress_repo,
    )
    mark_coach_mark_seen_use_case: Factory[
        UseCaseContract[CoachMarkSeenCommand, HelpProgressView]
    ] = Factory(
        MarkCoachMarkSeenUseCase,
        help_progress_repo=repositories.help_progress_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    reset_coach_marks_use_case: Factory[UseCaseContract[HelpProgressQuery, None]] = (
        Factory(
            ResetCoachMarksUseCase,
            help_progress_repo=repositories.help_progress_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    read_changelog_use_case: Factory[
        UseCaseContract[ChangelogReadCommand, HelpProgressView]
    ] = Factory(
        ReadChangelogUseCase,
        help_progress_repo=repositories.help_progress_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
