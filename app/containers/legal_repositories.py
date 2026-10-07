from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.legal_collections_container import (
    LegalCollectionsContainer,
)
from app.repositories.legal_repositories import (
    SubprocessorAnnouncementRepository,
    SubprocessorNoticeRepository,
)


class LegalRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the sub-processor change notices (migration 1124).
    `RepositoriesContainer` extends it, so they are read as
    `repositories.subprocessor_notice_repo` like every other repository.
    """

    legal_collections: LegalCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    subprocessor_notice_repo: Singleton[SubprocessorNoticeRepository] = Singleton(
        SubprocessorNoticeRepository,
        collection=legal_collections.subprocessor_notice_collection,
    )
    subprocessor_announcement_repo: Singleton[SubprocessorAnnouncementRepository] = (
        Singleton(
            SubprocessorAnnouncementRepository,
            collection=legal_collections.subprocessor_announcement_collection,
        )
    )
