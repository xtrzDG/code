"""The phone channel is turned off: the rented number goes back."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.phone_numbers import (
    PhoneLineLockRegistryContract,
    PhoneNumberRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.phone_numbers import (
    PhoneNumberReleaseReason,
    PhoneNumberStatus,
)
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.telephony.number_release import mark_releasing


class GiveBackPhoneNumberUseCase(UseCaseContract[BusinessId, None]):
    """
    Turning the phone channel off gives the business's rented number back
    (the cabinet says so before the owner confirms): the number becomes
    RELEASING at once, so no further rental month begins, and the
    maintenance job removes it from the voice platform and returns it to
    the carrier within minutes. A business without a rented number: nothing
    happens. Taken under the phone line lock, so a number being rented right
    now is never half given back.
    """

    def __init__(
        self,
        phone_number_repo: PhoneNumberRepoContract,
        phone_line_lock: PhoneLineLockRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._phone_number_repo: PhoneNumberRepoContract = phone_number_repo
        self._phone_line_lock: PhoneLineLockRegistryContract = phone_line_lock
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BusinessId) -> None:
        with self._phone_line_lock.lock_for(input_data):
            held: PhoneNumberDocument | None = self._phone_number_repo.find_held(
                input_data
            )
            if held is None or held.status is not PhoneNumberStatus.ACTIVE:
                return

            now: Microseconds = self._wall_clock.now_unix()
            self._phone_number_repo.modify(
                input_data,
                held.id,
                lambda stored: mark_releasing(
                    stored, PhoneNumberReleaseReason.OWNER, now
                ),
            )
