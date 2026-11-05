from dependency_injector.providers import Singleton

from app.containers.niche_texts.niche_text_root import NicheTextRoot
from app.containers.use_cases.closure_use_cases import ClosureUseCasesContainer
from app.containers.use_cases.core_use_cases_container import CoreUseCasesContainer
from app.containers.use_cases.niche_text_root_provider import (
    niche_text_root_provider,
)


class NicheTextUseCasesContainer(ClosureUseCasesContainer):
    """
    The platform admin's niche template editor (R17, migration 1221): one
    typed root (ADR 0010), whose operators the admin routes take.
    `UseCasesContainer` extends it.
    """

    niche_text_root: Singleton[NicheTextRoot] = niche_text_root_provider(
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
    )
