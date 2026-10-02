from typed_time_provider import Microseconds, WallClock

from app.contracts.demo_data import DemoDatasetRegistryContract
from app.contracts.repositories import BusinessRepoContract, UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.demo_data import (
    DemoAccounts,
    DemoBusinessFoundation,
    DemoFoundationRequest,
    DemoSeedPlan,
    SeedDemoDataCommand,
)
from app.schemas.typings.businesses.strings import BusinessName


class PrepareDemoAccountsUseCase(UseCaseContract[SeedDemoDataCommand, DemoSeedPlan]):
    """
    First step of seeding the development demo data (SEED_DEMO_DATA): find
    the demo owner and staff member by phone number or e-mail, or create
    them as verified accounts, and plan the demo businesses the owner does
    not have yet (matched by name). Running it again plans nothing new, so
    a restart on Postgres keeps the demo as it was.
    """

    def __init__(
        self,
        demo_dataset_registry: DemoDatasetRegistryContract,
        user_repo: UserRepoContract,
        business_repo: BusinessRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._demo_dataset_registry: DemoDatasetRegistryContract = demo_dataset_registry
        self._user_repo: UserRepoContract = user_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SeedDemoDataCommand) -> DemoSeedPlan:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        accounts: DemoAccounts = self._demo_dataset_registry.describe_accounts()
        owner: UserDocument = self._find_or_create(accounts.owner, now)
        staff: UserDocument = self._find_or_create(accounts.staff, now)
        existing: dict[BusinessName, BusinessDocument] = {
            business.name: business
            for business in self._business_repo.list_by_member(owner.id)
        }
        foundations: list[DemoBusinessFoundation] = (
            self._demo_dataset_registry.build_foundations(
                DemoFoundationRequest(owner_id=owner.id, staff_id=staff.id, now=now)
            )
        )
        return DemoSeedPlan(
            owner_id=owner.id,
            staff_id=staff.id,
            seeded_at=now,
            foundations=[
                foundation
                for foundation in foundations
                if foundation.business.name not in existing
            ],
            kept_business_ids=[
                existing[foundation.business.name].id
                for foundation in foundations
                if foundation.business.name in existing
            ],
        )

    def _find_or_create(self, account: UserDocument, now: Microseconds) -> UserDocument:
        found: UserDocument | None = None
        if account.phone_number is not None:
            found = self._user_repo.find_by_phone_number(account.phone_number)

        if found is None and account.email is not None:
            found = self._user_repo.find_by_email(account.email)

        if found is not None:
            return found

        account.created_at = now
        account.updated_at = now
        self._user_repo.save(account)
        return account
