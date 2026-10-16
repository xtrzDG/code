from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.setup_repositories import SetupStateRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.setup_guide import MarkSetupSharedCommand


class MarkSetupSharedUseCase(UseCaseContract[MarkSetupSharedCommand, None]):
    """
    The cabinet saw the owner (or a staff member) print the QR card or save
    the QR code: the guide's "Show customers where to write" step is done,
    and the day-10 reminder is not needed. Only the first time is kept.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        setup_state_repo: SetupStateRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._setup_state_repo: SetupStateRepoContract = setup_state_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: MarkSetupSharedCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        stored: SetupStateDocument | None = self._setup_state_repo.get_by_business(
            business.id
        )
        if stored is not None and stored.shared_at is not None:
            return

        now: Microseconds = self._wall_clock.now_unix()

        def mark(state: SetupStateDocument) -> None:
            if state.shared_at is None:
                state.shared_at = now

        self._setup_state_repo.change(business.id, mark, now)
