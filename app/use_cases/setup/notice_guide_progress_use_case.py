from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.setup_repositories import (
    SetupProbeRepoContract,
    SetupStateRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.setup.setup_guide import GuideProgressCheck
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.use_cases.setup.milestone_announcements import announce_milestone
from app.utilities.setup.phone_check import listening_window, owner_sender_ids


class NoticeGuideProgressUseCase(
    UseCaseContract[GuideProgressCheck, SetupStateDocument | None]
):
    """
    Notice, for a live business, what the guide after the launch waits for
    and no other record keeps, and store it once in its setup state:

    - the first message from the owner's own phone ("Try it from your
      phone"): a conversation from one of the owner's own senders, or one
      that starts while the guide listens (see `phone_check.py`);
    - the first booking made in a conversation after opening hours, a
      milestone announced to the team when it is new (once: setting it is
      a single change of the stored state, and the alert names it).

    Nothing is probed before the launch or once noticed. Returns the setup
    state as it stands then (None when the business has none).
    """

    def __init__(
        self,
        setup_state_repo: SetupStateRepoContract,
        setup_probe_repo: SetupProbeRepoContract,
        user_repo: UserRepoContract,
        staff_alerts: StaffAlertFacilitatorContract,
        localized_text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._setup_state_repo: SetupStateRepoContract = setup_state_repo
        self._setup_probe_repo: SetupProbeRepoContract = setup_probe_repo
        self._user_repo: UserRepoContract = user_repo
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: GuideProgressCheck) -> SetupStateDocument | None:
        business: BusinessDocument = input_data.business
        state: SetupStateDocument | None = self._setup_state_repo.get_by_business(
            business.id
        )
        if not input_data.is_live:
            return state

        tested_at: Microseconds | None = (
            self._find_phone_test(business, state)
            if state is None or state.phone_tested_at is None
            else None
        )
        after_hours_at: Microseconds | None = (
            self._setup_probe_repo.find_first_after_hours_booking_at(business.id)
            if state is None or state.after_hours_booking_at is None
            else None
        )
        if tested_at is None and after_hours_at is None:
            return state

        noticed: list[bool] = [False]

        def note(stored: SetupStateDocument) -> None:
            if tested_at is not None and stored.phone_tested_at is None:
                stored.phone_tested_at = tested_at

            noticed[0] = after_hours_at is not None and (
                stored.after_hours_booking_at is None
            )
            if noticed[0]:
                stored.after_hours_booking_at = after_hours_at

        now: Microseconds = self._wall_clock.now_unix()
        changed: SetupStateDocument = self._setup_state_repo.change(
            business.id, note, now
        )
        if noticed[0] and after_hours_at is not None:
            announce_milestone(
                self._staff_alerts,
                self._resolver,
                business,
                ActivationEventKind.FIRST_AFTER_HOURS_BOOKING,
                after_hours_at,
                now,
            )

        return changed

    def _find_phone_test(
        self,
        business: BusinessDocument,
        state: SetupStateDocument | None,
    ) -> Microseconds | None:
        senders: frozenset[ChannelUserId] = owner_sender_ids(
            business, self._owner_phones(business)
        )
        found: list[Microseconds] = []
        if senders:
            from_owner: Microseconds | None = (
                self._setup_probe_repo.find_first_conversation_from(
                    business.id, senders
                )
            )
            if from_owner is not None:
                found.append(from_owner)

        window = listening_window(state)
        if window is not None:
            in_window: Microseconds | None = (
                self._setup_probe_repo.find_first_conversation_between(
                    business.id, window[0], window[1]
                )
            )
            if in_window is not None:
                found.append(in_window)

        return min(found, default=None)

    def _owner_phones(self, business: BusinessDocument) -> list[E164PhoneNumber]:
        phones: list[E164PhoneNumber] = []
        for member in business.members:
            if member.role is not BusinessMemberRole.OWNER:
                continue

            user: UserDocument | None = self._user_repo.get(member.user_id)
            if user is not None and user.phone_number is not None:
                phones.append(user.phone_number)

        return phones
