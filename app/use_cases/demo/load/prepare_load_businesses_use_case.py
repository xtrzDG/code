from typed_time_provider import Microseconds, WallClock

from app.contracts.demo_data import DemoDatasetRegistryContract
from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.dto.demo_data import DemoBusinessFoundation, DemoFoundationRequest
from app.schemas.dto.load_data import (
    LoadBusinessPlan,
    LoadBusinessShare,
    LoadSeedPlan,
    SeedLoadCommand,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.demo.constrained_integers import (
    LoadBookingCount,
    LoadBusinessIndex,
    LoadMessageCount,
    LoadRandomSeed,
    LoadVisitorCount,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import AccessToken, UserDisplayName
from app.utilities.security.access_tokens import (
    generate_access_token,
    hash_access_token,
)

# Load-test sessions outlive a long weekly run.
SESSION_LIFETIME_MICROSECONDS: int = 30 * 24 * 3_600 * 1_000_000
# Spreads the random seeds of the businesses of one run far apart.
BUSINESS_SEED_STRIDE: int = 1_000_003
SEED_MODULUS: int = 2_147_483_647
LOAD_EMAIL_DOMAIN: str = "load.example.com"


def split_evenly(total: int, parts: int, index: int) -> int:
    """Part `index` of `total` split into `parts` (the first ones get one more)."""

    share, remainder = divmod(total, parts)
    return share + (1 if index < remainder else 0)


class PrepareLoadBusinessesUseCase(UseCaseContract[SeedLoadCommand, LoadSeedPlan]):
    """
    First step of `workshop seed-load`: for every load business a new,
    verified owner and staff member (e-mails under load.example.com, unique
    per run), a signed-in session of the owner (the load tests use its
    bearer token), the demo foundation the business is built from (the
    Tbilisi restaurant and the Berlin salon in turn, numbered names) and
    its even share of the messages, bookings and widget visitors.
    """

    def __init__(
        self,
        demo_dataset_registry: DemoDatasetRegistryContract,
        user_repo: UserRepoContract,
        user_session_repo: UserSessionRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._registry: DemoDatasetRegistryContract = demo_dataset_registry
        self._user_repo: UserRepoContract = user_repo
        self._session_repo: UserSessionRepoContract = user_session_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SeedLoadCommand) -> LoadSeedPlan:
        now: Microseconds = self._wall_clock.now_unix()
        count: int = int(input_data.business_count)
        return LoadSeedPlan(
            seeded_at=now,
            businesses=[
                self._plan_business(input_data, index, count, now)
                for index in range(count)
            ],
        )

    def _plan_business(
        self,
        command: SeedLoadCommand,
        index: int,
        count: int,
        now: Microseconds,
    ) -> LoadBusinessPlan:
        owner: UserDocument = self._create_user("owner", index, now)
        staff: UserDocument = self._create_user("staff", index, now)
        foundations: list[DemoBusinessFoundation] = self._registry.build_foundations(
            DemoFoundationRequest(owner_id=owner.id, staff_id=staff.id, now=now)
        )
        foundation: DemoBusinessFoundation = foundations[index % len(foundations)]
        foundation.business.name = BusinessName(
            f"{foundation.business.name} {index + 1}"
        )
        return LoadBusinessPlan(
            index=LoadBusinessIndex(index),
            owner_id=owner.id,
            owner_access_token=self._sign_in(owner, now),
            foundation=foundation,
            share=LoadBusinessShare(
                message_count=LoadMessageCount(
                    split_evenly(int(command.message_count), count, index)
                ),
                booking_count=LoadBookingCount(
                    split_evenly(int(command.booking_count), count, index)
                ),
                visitor_count=LoadVisitorCount(
                    split_evenly(int(command.visitor_count), count, index)
                ),
            ),
            random_seed=LoadRandomSeed(
                (int(command.random_seed) * BUSINESS_SEED_STRIDE + index) % SEED_MODULUS
            ),
        )

    def _create_user(self, role: str, index: int, now: Microseconds) -> UserDocument:
        run: int = int(now) // 1_000_000
        user = UserDocument(
            login_method=LoginMethod.EMAIL,
            email=EmailAddress(f"{role}-{run}-{index}@{LOAD_EMAIL_DOMAIN}"),
            country_code=CountryCode("GE"),
            locale=LanguageTag("en"),
            display_name=UserDisplayName(f"Load {role} {index + 1}"),
            is_verified=True,
            created_at=now,
            updated_at=now,
        )
        self._user_repo.save(user)
        return user

    def _sign_in(self, owner: UserDocument, now: Microseconds) -> AccessToken:
        token: AccessToken = generate_access_token()
        self._session_repo.save(
            UserSessionDocument(
                user_id=owner.id,
                token_hash=hash_access_token(token),
                expires_at=Microseconds(int(now) + SESSION_LIFETIME_MICROSECONDS),
                created_at=now,
                updated_at=now,
            )
        )
        return token
