"""
Sign-in in production: the bot check of code requests with live
Cloudflare Turnstile keys and login codes by e-mail only over an encrypted
connection. (At least one channel that carries codes is checked at startup
against the configured providers, `app/gateways/startup_checks.py`.)
"""

import re

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.typings.platform.strings import ProductionSettingProblem

# Cloudflare's published Turnstile test keys (always pass, always fail,
# "token already spent", forced challenge): "1x00000000000000000000AA",
# "2x0000000000000000000000000000000AA" and their siblings. Live keys start
# with "0x".
TURNSTILE_TEST_KEY_PATTERN: re.Pattern[str] = re.compile(r"^[1-3]x0{10,}[A-F]{2}$")


def find_sign_in_problems(settings: AppSettings) -> list[ProductionSettingProblem]:
    problems: list[ProductionSettingProblem] = []
    if settings.turnstile_site_key is None or settings.turnstile_secret_key is None:
        problems.append(
            ProductionSettingProblem(
                "TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY are not set: "
                "production never sends login codes without the bot check "
                "(SMS pumping); create a Cloudflare Turnstile widget."
            )
        )
    else:
        for name, key in (
            ("TURNSTILE_SITE_KEY", str(settings.turnstile_site_key)),
            ("TURNSTILE_SECRET_KEY", str(settings.turnstile_secret_key)),
        ):
            if TURNSTILE_TEST_KEY_PATTERN.fullmatch(key.strip()) is not None:
                problems.append(
                    ProductionSettingProblem(
                        f"{name} is one of Cloudflare's test keys, which pass "
                        "(or fail) every check: use the widget's live keys."
                    )
                )
    if settings.smtp_security is SmtpSecurity.NONE:
        problems.append(
            ProductionSettingProblem(
                "SMTP_SECURITY=none sends login codes and passwords unencrypted: "
                "use starttls or ssl in production."
            )
        )

    return problems
