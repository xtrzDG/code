"""
Live payment credentials and the verification secrets of every enabled
provider: production never takes a PSP's test keys or published test
merchant, and never runs a feature whose webhooks it could not verify
(each of them would then refuse every delivery, or worse).
"""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.typings.platform.strings import ProductionSettingProblem

# Stripe's test-mode keys (secret, restricted) and any publishable key,
# which is no secret at all.
STRIPE_REFUSED_KEY_PREFIXES: dict[str, str] = {
    "sk_test_": "a test-mode key",
    "rk_test_": "a test-mode key",
    "pk_": "a publishable key, not a secret one",
}
# Flitt's documented test merchant and its published key (Flitt's docs,
# tests/contracts/README.md): anyone can sign its callbacks.
FLITT_TEST_MERCHANT_ID: str = "1549901"
FLITT_PUBLISHED_TEST_VALUE: str = "test"


def find_provider_secret_problems(
    settings: AppSettings,
) -> list[ProductionSettingProblem]:
    problems: list[ProductionSettingProblem] = [
        *find_payment_problems(settings),
        *(
            ProductionSettingProblem(f"{needed} is not set, but {because} is: {why}.")
            for needed, because, why in missing_verification_secrets(settings)
        ),
    ]
    return problems


def find_payment_problems(settings: AppSettings) -> list[ProductionSettingProblem]:
    problems: list[ProductionSettingProblem] = []
    stripe_key: str = str(settings.payments.stripe_secret_key or "").strip()
    for prefix, kind in STRIPE_REFUSED_KEY_PREFIXES.items():
        if stripe_key.startswith(prefix):
            problems.append(
                ProductionSettingProblem(
                    f"STRIPE_SECRET_KEY is {kind} ({prefix}...): production "
                    "takes the live secret or restricted key (sk_live_, rk_live_)."
                )
            )
    if str(settings.flitt_merchant_id or "").strip() == FLITT_TEST_MERCHANT_ID:
        problems.append(
            ProductionSettingProblem(
                f"FLITT_MERCHANT_ID is Flitt's test merchant "
                f"{FLITT_TEST_MERCHANT_ID}: use your own merchant."
            )
        )
    if str(settings.flitt_secret_key or "").strip() == FLITT_PUBLISHED_TEST_VALUE:
        problems.append(
            ProductionSettingProblem(
                "FLITT_SECRET_KEY is the test merchant's published key: anyone "
                "could sign a payment notification with it."
            )
        )

    return problems


def missing_verification_secrets(
    settings: AppSettings,
) -> list[tuple[str, str, str]]:
    """`(missing variable, the variable that enables it, why)` of each gap."""

    is_meta_enabled: bool = any(
        value is not None
        for value in (
            settings.meta_app_id,
            settings.meta_embedded_signup_config_id,
            settings.whatsapp_system_user_token,
        )
    )
    meta_cause: str = "META_APP_ID or WHATSAPP_SYSTEM_USER_TOKEN"
    gaps: list[tuple[bool, str, str, str]] = [
        (
            settings.payments.stripe_secret_key is not None
            and settings.payments.stripe_webhook_secret is None,
            "STRIPE_WEBHOOK_SECRET",
            "STRIPE_SECRET_KEY",
            "no Stripe notification could be verified, so nothing is marked paid",
        ),
        (
            (settings.flitt_merchant_id is None) != (settings.flitt_secret_key is None),
            "FLITT_SECRET_KEY"
            if settings.flitt_secret_key is None
            else "FLITT_MERCHANT_ID",
            "FLITT_MERCHANT_ID"
            if settings.flitt_secret_key is None
            else "FLITT_SECRET_KEY",
            "Flitt signs its payments and callbacks with the merchant's key",
        ),
        (
            is_meta_enabled and settings.meta_app_secret is None,
            "META_APP_SECRET",
            meta_cause,
            "WhatsApp, Instagram and Messenger webhooks are verified with it",
        ),
        (
            is_meta_enabled and settings.meta_verify_token is None,
            "META_VERIFY_TOKEN",
            meta_cause,
            "Meta confirms the webhook subscription with it",
        ),
        (
            settings.elevenlabs_api_key is not None
            and settings.elevenlabs_webhook_secret is None,
            "ELEVENLABS_WEBHOOK_SECRET",
            "ELEVENLABS_API_KEY",
            "the voice agent's calls and tools are verified with it",
        ),
        (
            (settings.zadarma_api_key is None) != (settings.zadarma_api_secret is None),
            "ZADARMA_API_SECRET"
            if settings.zadarma_api_secret is None
            else "ZADARMA_API_KEY",
            "ZADARMA_API_KEY"
            if settings.zadarma_api_secret is None
            else "ZADARMA_API_SECRET",
            "Zadarma signs its requests and notifications with the pair",
        ),
        (
            (settings.google_oauth_client_id is None)
            != (settings.google_oauth_client_secret is None),
            "GOOGLE_OAUTH_CLIENT_SECRET"
            if settings.google_oauth_client_secret is None
            else "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_ID"
            if settings.google_oauth_client_secret is None
            else "GOOGLE_OAUTH_CLIENT_SECRET",
            "Google Calendar's consent needs the client's id and secret",
        ),
    ]
    return [(needed, because, why) for is_gap, needed, because, why in gaps if is_gap]
