"""
Sign-in in production: the bot check of code requests with live
Cloudflare Turnstile keys, login codes by e-mail only over an encrypted
connection, login codes valid ten minutes at most, and platform admins on
passkeys (phishing resistant). (At least one channel that carries codes is
checked at startup against the configured providers,
`app/gateways/startup_checks.py`.)
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
# Out-of-band codes live ten minutes at most (OWASP ASVS 5.0 V6.6.3).
MAX_PRODUCTION_OTP_LIFETIME_SECONDS: int = 10 * 60


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
    if int(settings.otp_lifetime_seconds) > MAX_PRODUCTION_OTP_LIFETIME_SECONDS:
        problems.append(
            ProductionSettingProblem(
                f"OTP_LIFETIME_SECONDS={int(settings.otp_lifetime_seconds)} keeps a "
                "login code valid longer than ten minutes: use "
                f"{MAX_PRODUCTION_OTP_LIFETIME_SECONDS} or less in production."
            )
        )
    if not settings.sessions.is_admin_passkey_required:
        problems.append(
            ProductionSettingProblem(
                "ADMIN_PASSKEY_REQUIRED=false lets platform admins in with the "
                "authenticator app's code alone, which can be phished: remove it."
            )
        )
    elif settings.sessions.webauthn_rp_id is None and settings.cabinet_base_url:
        # Without a cabinet address that problem is named on its own
        # (address_requirements.py); passkeys follow once it is set.
        problems.append(
            ProductionSettingProblem(
                "ADMIN_PASSKEY_REQUIRED needs passkeys, and none can be offered: "
                "set WEBAUTHN_RP_ID (or a CABINET_BASE_URL with a domain name)."
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
