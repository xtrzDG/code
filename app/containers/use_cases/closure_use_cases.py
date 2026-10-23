from dependency_injector.providers import Singleton

from app.containers.account_deletion.account_deletion_root import AccountDeletionRoot
from app.containers.use_cases.account_deletion_root_provider import (
    account_deletion_root_provider,
)
from app.containers.use_cases.business_use_cases_container import (
    BusinessUseCasesContainer,
)
from app.containers.use_cases.core_use_cases_container import CoreUseCasesContainer


class ClosureUseCasesContainer(BusinessUseCasesContainer):
    """
    Closing and deleting businesses, deleting accounts (R15, migration
    1220): one typed root (ADR 0010) over a business's own work, whose
    operators the routers and the worker take (`GatewaysContainer`).
    `UseCasesContainer` extends it.
    """

    account_deletion_root: Singleton[AccountDeletionRoot] = (
        account_deletion_root_provider(
            adapters=CoreUseCasesContainer.adapters,
            clients=CoreUseCasesContainer.clients,
            config=CoreUseCasesContainer.config,
            facilitators=CoreUseCasesContainer.facilitators,
            registries=CoreUseCasesContainer.registries,
            repositories=CoreUseCasesContainer.repositories,
            time_provider=CoreUseCasesContainer.time_provider,
            utilities=CoreUseCasesContainer.utilities,
            account_use_cases=CoreUseCasesContainer.accounts,
            assistant_use_cases=BusinessUseCasesContainer.assistants,
            scheduling_use_cases=CoreUseCasesContainer.scheduling,
            voice_use_cases=BusinessUseCasesContainer.voice,
        )
    )
