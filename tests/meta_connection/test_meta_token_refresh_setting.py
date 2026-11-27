"""META_TOKEN_REFRESH_DAYS: how early WhatsApp Embedded Signup tokens are renewed."""

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.meta_connection.constrained_integers import (
    MetaTokenRefreshDays,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)


def test_tokens_are_renewed_fifteen_days_early_unless_set() -> None:
    assert assemble_app_settings({}).meta_token_refresh_days == MetaTokenRefreshDays(15)
    for days in ("1", "60"):
        settings = assemble_app_settings({"META_TOKEN_REFRESH_DAYS": days})
        assert settings.meta_token_refresh_days == MetaTokenRefreshDays(int(days))


@pytest.mark.parametrize("days", ["0", "61", "two weeks"])
def test_a_window_meta_would_not_honour_stops_the_start(days: str) -> None:
    with pytest.raises(ValidationFailedError, match="META_TOKEN_REFRESH_DAYS"):
        assemble_app_settings({"META_TOKEN_REFRESH_DAYS": days})
