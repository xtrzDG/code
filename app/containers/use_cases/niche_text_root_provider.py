from dependency_injector.providers import Factory, Singleton

from app.containers.niche_texts.niche_text_dependencies import NicheTextDependencies
from app.containers.niche_texts.niche_text_root import NicheTextRoot
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer


def niche_text_root_provider(
    *,
    registries: RegistriesContainer,
    repositories: RepositoriesContainer,
    time_provider: TimeProviderContainer,
    utilities: UtilitiesContainer,
) -> Singleton[NicheTextRoot]:
    """
    The niche template editor's one root (migration 1221), its dependencies
    taken from the graph: the single seam between the providers and the
    typed root (app/containers/niche_texts/, ADR 0010; a missing or
    misspelt field fails test_every_provider_of_the_container_resolves).
    """

    return Singleton(
        NicheTextRoot,
        dependencies=Factory(
            NicheTextDependencies,
            niche_templates=registries.niche_template_registry,
            starter_answers=registries.starter_answer_registry,
            niche_text_repo=repositories.niche_text_repo,
            user_repo=repositories.user_repo,
            audit_log_repo=repositories.audit_log_repo,
            session_assurance=utilities.session_assurance,
            platform_admins=registries.platform_admin_registry,
            step_up=utilities.step_up_guard,
            localized_text_resolver=utilities.localized_text_resolver,
            storage_scope=utilities.storage_scope,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
    )
