"""One check-limit policy for login codes and second factors."""

import pytest
from typed_time_provider import Microseconds

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.registries.limits.request_rate_limit_registry import (
    RequestRateLimitRegistry,
)
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.use_cases.users.check_limit_policy import CHECK_WINDOW_SECONDS
from app.use_cases.users.mfa.mfa_check_limits import (
    CHECKS_PER_SUBJECT,
    refuse_too_frequent_second_factor_checks,
)
from app.use_cases.users.otp_login.login_check_limits import (
    CHECKS_PER_CHALLENGE,
    refuse_too_frequent_code_checks,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

NOW: Microseconds = Microseconds(1_760_000_000_000_000)
ADDRESS: ClientIpAddress = ClientIpAddress("203.0.113.7")
SETTINGS = assemble_app_settings({"OTP_VERIFIES_PER_IP_PER_10_MINUTES": "6"})


def registry() -> RequestRateLimitRegistry:
    return RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())


def test_login_codes_and_second_factors_share_one_network_budget() -> None:
    limits = registry()
    for number in range(3):
        refuse_too_frequent_code_checks(
            limits, SETTINGS, OtpChallengeId(), ADDRESS, NOW
        )
        refuse_too_frequent_second_factor_checks(
            limits, SETTINGS, RateLimitKey(f"mfa-check:step:{number}"), ADDRESS, NOW
        )

    # Six checks of six subjects used the address's six: any kind is refused.
    with pytest.raises(RateLimitedError) as login_refused:
        refuse_too_frequent_code_checks(
            limits, SETTINGS, OtpChallengeId(), ADDRESS, NOW
        )
    with pytest.raises(RateLimitedError):
        refuse_too_frequent_second_factor_checks(
            limits, SETTINGS, RateLimitKey("mfa-check:step:9"), ADDRESS, NOW
        )
    assert (
        0
        < int(login_refused.value.retry_after_seconds or 0)
        <= int(CHECK_WINDOW_SECONDS)
    )


@pytest.mark.parametrize("client_ip_address", [None, ADDRESS])
def test_each_subject_has_its_own_budget_with_or_without_an_address(
    client_ip_address: ClientIpAddress | None,
) -> None:
    settings = assemble_app_settings({"OTP_VERIFIES_PER_IP_PER_10_MINUTES": "100"})
    limits = registry()
    subject = RateLimitKey("mfa-check:person:1")
    login_challenge, other_challenge = OtpChallengeId(), OtpChallengeId()
    for _ in range(int(CHECKS_PER_SUBJECT)):
        refuse_too_frequent_second_factor_checks(
            limits, settings, subject, client_ip_address, NOW
        )
    for _ in range(int(CHECKS_PER_CHALLENGE)):
        refuse_too_frequent_code_checks(
            limits, settings, login_challenge, client_ip_address, NOW
        )

    with pytest.raises(RateLimitedError):
        refuse_too_frequent_second_factor_checks(
            limits, settings, subject, client_ip_address, NOW
        )
    with pytest.raises(RateLimitedError):
        refuse_too_frequent_code_checks(
            limits, settings, login_challenge, client_ip_address, NOW
        )
    # Another subject still has its whole budget.
    refuse_too_frequent_code_checks(
        limits, settings, other_challenge, client_ip_address, NOW
    )
