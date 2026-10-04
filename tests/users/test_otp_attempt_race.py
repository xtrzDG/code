"""
Parallel code checks of one challenge: at most `otp_max_failed_attempts`
of them are compared with the code, and a right code opens one session.

Each read of the challenge waits like a database round trip, so the checks
really overlap (before the fix, 40 parallel wrong guesses were all compared
and the stored count ended at 1).
"""

import threading
import time
from collections.abc import Callable

import pytest
from typed_time_provider import Microseconds

from app.repositories.user_repositories import OtpChallengeRepository
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.dto.users import VerifyOtpLoginCommand
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    RateLimitedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.schemas.typings.users.strings import OtpCodeHash
from app.use_cases.users.otp_login import login_challenge_consumption
from app.utilities.security.one_time_codes import is_otp_code_matching
from tests.users.accounts_phones import GEORGIA_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

GUESS_COUNT: int = 40
READ_DELAY_SECONDS: float = 0.02


def slow_down_reads(repo: OtpChallengeRepository) -> None:
    """Every read of a challenge takes a database round trip."""

    read: Callable[[OtpChallengeId], OtpChallengeDocument | None] = repo.get

    def slow_read(challenge_id: OtpChallengeId) -> OtpChallengeDocument | None:
        challenge = read(challenge_id)
        time.sleep(READ_DELAY_SECONDS)
        return challenge

    repo.get = slow_read  # type: ignore[method-assign]


def count_comparisons(monkeypatch: pytest.MonkeyPatch) -> list[OtpCode]:
    """Record every code the use case compares with the stored hash."""

    compared: list[OtpCode] = []

    def counting_compare(
        challenge_id: OtpChallengeId, code: OtpCode, code_hash: OtpCodeHash
    ) -> bool:
        compared.append(code)
        return is_otp_code_matching(challenge_id, code, code_hash)

    monkeypatch.setattr(
        login_challenge_consumption, "is_otp_code_matching", counting_compare
    )
    return compared


def wrong_codes(correct_code: OtpCode, count: int) -> list[OtpCode]:
    return [
        OtpCode(f"{guess:06d}")
        for guess in range(count + 1)
        if OtpCode(f"{guess:06d}") != correct_code
    ][:count]


def check_in_parallel(
    testbed: AccountsTestbed,
    challenge_id: OtpChallengeId,
    codes: list[OtpCode],
) -> dict[str, int]:
    """Send every code at once (one thread each); count the outcomes."""

    outcomes: dict[str, int] = {"signed_in": 0, "wrong": 0, "refused": 0}
    lock = threading.Lock()
    start = threading.Barrier(len(codes))

    def check(code: OtpCode, index: int) -> None:
        start.wait()
        try:
            testbed.verify_otp_login.run(
                VerifyOtpLoginCommand(
                    challenge_id=challenge_id,
                    code=code,
                    # Spread over networks, as a botnet would.
                    client_ip_address=ClientIpAddress(f"203.0.113.{index}"),
                )
            )
            outcome = "signed_in"
        except AuthenticationRequiredError:
            outcome = "wrong"
        except RateLimitedError:
            outcome = "refused"
        with lock:
            outcomes[outcome] += 1

    threads = [
        threading.Thread(target=check, args=(code, index))
        for index, code in enumerate(codes)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return outcomes


def test_forty_parallel_wrong_guesses_lock_the_challenge_after_five(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = build_accounts_testbed({"OTP_MAX_FAILED_ATTEMPTS": "5"})
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)
    correct_code = testbed.otp_delivery.last_code()
    slow_down_reads(testbed.otp_challenge_repo)
    compared = count_comparisons(monkeypatch)

    outcomes = check_in_parallel(
        testbed,
        challenge.challenge_id,
        wrong_codes(correct_code, GUESS_COUNT),
    )

    assert outcomes == {"signed_in": 0, "wrong": 5, "refused": GUESS_COUNT - 5}
    assert len(compared) == 5
    stored = testbed.otp_challenge_repo.get(challenge.challenge_id)
    assert stored is not None
    assert stored.failed_attempts == 5
    assert not stored.is_consumed


def test_parallel_guesses_with_the_right_code_compare_at_most_five_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = build_accounts_testbed({"OTP_MAX_FAILED_ATTEMPTS": "5"})
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)
    correct_code = testbed.otp_delivery.last_code()
    slow_down_reads(testbed.otp_challenge_repo)
    compared = count_comparisons(monkeypatch)

    codes = [*wrong_codes(correct_code, GUESS_COUNT - 1), correct_code]
    outcomes = check_in_parallel(testbed, challenge.challenge_id, codes)

    assert len(compared) <= 5
    # The right code signs in only when it was one of the compared codes.
    assert outcomes["signed_in"] == (1 if correct_code in compared else 0)
    stored = testbed.otp_challenge_repo.get(challenge.challenge_id)
    assert stored is not None
    assert stored.failed_attempts <= 5


def test_the_same_right_code_sent_twice_at_once_opens_one_session() -> None:
    testbed = build_accounts_testbed()
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)
    correct_code = testbed.otp_delivery.last_code()
    slow_down_reads(testbed.otp_challenge_repo)

    outcomes = check_in_parallel(testbed, challenge.challenge_id, [correct_code] * 4)

    assert outcomes == {"signed_in": 1, "wrong": 3, "refused": 0}
    stored = testbed.otp_challenge_repo.get(challenge.challenge_id)
    assert stored is not None
    assert stored.is_consumed


def test_a_right_code_consumed_by_a_parallel_check_opens_no_second_session() -> None:
    testbed = build_accounts_testbed()
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)
    correct_code = testbed.otp_delivery.last_code()
    repo = testbed.otp_challenge_repo
    consume = repo.consume

    def consumed_meanwhile(
        challenge_id: OtpChallengeId, now: Microseconds
    ) -> OtpChallengeDocument | None:
        consume(challenge_id, now)  # The parallel check wins the swap.
        return consume(challenge_id, now)

    repo.consume = consumed_meanwhile  # type: ignore[method-assign]

    with pytest.raises(AuthenticationRequiredError):
        testbed.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id, code=correct_code
            )
        )

    assert (
        testbed.user_repo.find_by_phone_number(E164PhoneNumber("+995555123456")) is None
    )
