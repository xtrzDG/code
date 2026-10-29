"""STEP_UP_MAX_AGE_SECONDS and MFA_ISSUER_NAME: two-factor sign-in."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.typings.mfa.constrained_integers import StepUpMaxAgeSeconds
from app.schemas.typings.mfa.strings import TotpIssuerName
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_integer,
    read_text,
)

DEFAULT_STEP_UP_MAX_AGE_SECONDS: int = 10 * 60
DEFAULT_MFA_ISSUER_NAME: str = "Assistant Workshop"


class MfaSettingsSection(TypedDict):
    """The `AppSettings` fields of two-factor sign-in and step-up."""

    step_up_max_age_seconds: StepUpMaxAgeSeconds
    mfa_issuer_name: TotpIssuerName


def read_mfa_settings(
    environment_variables: Mapping[str, str],
) -> MfaSettingsSection:
    return MfaSettingsSection(
        step_up_max_age_seconds=parse_setting(
            "STEP_UP_MAX_AGE_SECONDS",
            read_integer(
                environment_variables,
                "STEP_UP_MAX_AGE_SECONDS",
                DEFAULT_STEP_UP_MAX_AGE_SECONDS,
            ),
            StepUpMaxAgeSeconds,
        ),
        mfa_issuer_name=TotpIssuerName(
            read_text(environment_variables, "MFA_ISSUER_NAME", DEFAULT_MFA_ISSUER_NAME)
        ),
    )
