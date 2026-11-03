"""
Automatic throttling of login codes to new phones when few of them are
used (VOICE-03): SMS pumping requests codes nobody types in, so a country
or a number range whose codes go unused gets fewer codes, then none.

Only settled codes count (used, or expired unused) among the codes to new
phones of the last six hours (`CONVERSION_WINDOW_SECONDS`): a verified
owner's code and an e-mail never trip it. The window is longer than the
hour of the send caps on purpose: a burst of codes sent before any of them
expires stays visible after it, so the range stays denied and the country
stays at its lowered cap while the burst's codes are in the window,
instead of opening again as soon as they are an hour old. The throttle
needs no stored state: a refused request creates no code, so a range or
country opens again once its unused codes leave the window.
"""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.schemas.constants.users import LoginCodeCap, LoginMethod
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.dto.login_protection import LoginCodeCapAlert, LoginCodeDestination
from app.schemas.exceptions.login_errors import LoginCodeCapReachedError
from app.schemas.typings.localization.constrained_strings import PhoneNumberPrefix
from app.schemas.typings.users.constrained_integers import OtpSendLimit

THROTTLED_MESSAGE: str = "Too many login codes were requested. Try again later."
MICROSECONDS_PER_SECOND: int = 1_000_000
# How far back the conversion of a country or a number range is measured.
CONVERSION_WINDOW_SECONDS: int = 6 * 60 * 60
# The lowered cap of a country counts its codes to new phones of the hour.
CAP_WINDOW_SECONDS: int = 60 * 60
# A country needs this many settled codes in the window before its
# conversion counts; under the floor (a share of used codes, in percent)
# its hourly cap of codes to new phones drops to the throttled cap.
COUNTRY_MIN_SETTLED: int = 20
COUNTRY_CONVERSION_FLOOR_PERCENT: int = 30
THROTTLED_SENDS_PER_COUNTRY_PER_HOUR: OtpSendLimit = OtpSendLimit(10)
# A number range is the first characters of the E.164 number ("+" and six
# digits: a calling code and the start of a network's range). Under its
# floor no new code goes to the range until its unused codes leave the
# window.
RANGE_PREFIX_LENGTH: int = 7
RANGE_MIN_SETTLED: int = 10
RANGE_CONVERSION_FLOOR_PERCENT: int = 10
DENIED_RANGE_LIMIT: OtpSendLimit = OtpSendLimit(1)


def refuse_over_conversion_throttle(
    list_lookback: Callable[[], list[OtpChallengeDocument]],
    destination: LoginCodeDestination,
    now: Microseconds,
) -> None:
    """
    Refuse a code to a new phone whose number range converts under its
    floor, or whose country converts under its floor and already had the
    throttled cap of codes this hour (a lower OTP_SENDS_PER_COUNTRY_PER_HOUR
    refuses first). `list_lookback` reads the challenges of the conversion
    window; it is called only for a new phone.

    Raises:
        LoginCodeCapReachedError: the platform team is alerted with the
            cap (`number_range_conversion` or `country_conversion`).
    """

    if (
        destination.is_verified_destination
        or destination.login_method is not LoginMethod.PHONE
        or destination.phone_number is None
    ):
        return

    new_phones: list[OtpChallengeDocument] = [
        challenge
        for challenge in list_lookback()
        if challenge.login_method is LoginMethod.PHONE
        and not challenge.is_verified_destination
    ]
    number_range: PhoneNumberPrefix = find_number_range(str(destination.phone_number))
    in_range: list[OtpChallengeDocument] = [
        challenge
        for challenge in new_phones
        if challenge.phone_number is not None
        and str(challenge.phone_number).startswith(str(number_range))
    ]
    if converts_under(in_range, now, RANGE_MIN_SETTLED, RANGE_CONVERSION_FLOOR_PERCENT):
        raise LoginCodeCapReachedError(
            THROTTLED_MESSAGE,
            alert=LoginCodeCapAlert(
                cap=LoginCodeCap.NUMBER_RANGE_CONVERSION,
                limit=DENIED_RANGE_LIMIT,
                country_code=destination.country_code,
                phone_number_prefix=number_range,
            ),
        )

    in_country: list[OtpChallengeDocument] = [
        challenge
        for challenge in new_phones
        if challenge.country_code == destination.country_code
    ]
    hour_start: int = int(now) - CAP_WINDOW_SECONDS * MICROSECONDS_PER_SECOND
    sent_this_hour: int = len(
        [
            challenge
            for challenge in in_country
            if int(challenge.created_at) > hour_start
        ]
    )
    if sent_this_hour >= int(THROTTLED_SENDS_PER_COUNTRY_PER_HOUR) and converts_under(
        in_country, now, COUNTRY_MIN_SETTLED, COUNTRY_CONVERSION_FLOOR_PERCENT
    ):
        raise LoginCodeCapReachedError(
            THROTTLED_MESSAGE,
            alert=LoginCodeCapAlert(
                cap=LoginCodeCap.COUNTRY_CONVERSION,
                limit=THROTTLED_SENDS_PER_COUNTRY_PER_HOUR,
                country_code=destination.country_code,
            ),
        )


def find_number_range(phone_number: str) -> PhoneNumberPrefix:
    """The number range of an E.164 number: its first seven characters."""

    return PhoneNumberPrefix(phone_number[:RANGE_PREFIX_LENGTH])


def converts_under(
    challenges: list[OtpChallengeDocument],
    now: Microseconds,
    min_settled: int,
    floor_percent: int,
) -> bool:
    """
    At least `min_settled` of `challenges` are settled (used, or expired
    unused at `now`) and under `floor_percent` of the settled were used.
    """

    settled: list[OtpChallengeDocument] = [
        challenge
        for challenge in challenges
        if challenge.is_consumed or int(challenge.expires_at) <= int(now)
    ]
    used: int = len([challenge for challenge in settled if challenge.is_consumed])
    return len(settled) >= min_settled and 100 * used < floor_percent * len(settled)
