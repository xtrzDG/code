"""
Production answers with a real model whose keys are set, takes live payment
credentials only, and never runs a feature whose webhooks it could not
verify.
"""

import pytest

from tests.platform.production_settings import problems_with


def test_the_scripted_model_is_refused() -> None:
    assert problems_with({"LLM_PROVIDER": "scripted"}) == [
        "LLM_PROVIDER=scripted answers every customer with one fixed sentence: "
        "production needs openai or anthropic."
    ]


def test_the_providers_key_is_required() -> None:
    [problem] = problems_with({"OPENAI_API_KEY": "  "})

    assert problem == "LLM_PROVIDER=openai needs OPENAI_API_KEY, which is not set."


def test_an_anthropic_deployment_needs_both_keys() -> None:
    without_keys = problems_with({"LLM_PROVIDER": "anthropic", "OPENAI_API_KEY": None})
    with_keys = problems_with(
        {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "anthropic-fake-key"}
    )

    assert without_keys[0] == (
        "LLM_PROVIDER=anthropic needs ANTHROPIC_API_KEY, which is not set."
    )
    # Voice notes and the menu photo import always call OpenAI.
    assert without_keys[1].startswith("OPENAI_API_KEY is not set: voice notes")
    assert with_keys == []


@pytest.mark.parametrize(
    "variable",
    [
        "LLM_MODEL_ID",
        "LLM_JUDGE_MODEL_ID",
        "LLM_SUMMARY_MODEL_ID",
        "LLM_VERIFIER_MODEL_ID",
        "SPEND_SOFT_LIMIT_MODEL_ID",
    ],
)
def test_a_configured_model_needs_its_providers_key(variable: str) -> None:
    [problem] = problems_with({variable: "claude-haiku-4-5"})
    offline = problems_with({variable: "scripted"})

    assert problem == (
        f"{variable}=claude-haiku-4-5 needs ANTHROPIC_API_KEY, which is not set."
    )
    assert offline == [f"{variable}=scripted is not a model of OpenAI or Anthropic."]


def test_a_fallback_without_its_key_is_no_reason_to_refuse() -> None:
    # It is skipped with a warning instead (test_llm_key_rules.py).
    assert problems_with({"LLM_FALLBACK_MODEL_ID": "claude-sonnet-5-5"}) == []


@pytest.mark.parametrize(
    ("key", "kind"),
    [
        ("sk_test_123", "a test-mode key"),
        ("rk_test_123", "a test-mode key"),
        ("pk_live_123", "a publishable key"),
    ],
)
def test_stripe_test_and_publishable_keys_are_refused(key: str, kind: str) -> None:
    [problem] = problems_with(
        {"STRIPE_SECRET_KEY": key, "STRIPE_WEBHOOK_SECRET": "whsec_fake"}
    )

    assert problem.startswith(f"STRIPE_SECRET_KEY is {kind}")
    assert key not in problem


def test_live_stripe_keys_with_their_webhook_secret_pass() -> None:
    live = {"STRIPE_SECRET_KEY": "sk_live_123", "STRIPE_WEBHOOK_SECRET": "whsec_fake"}

    assert problems_with(live) == []
    assert problems_with({**live, "STRIPE_WEBHOOK_SECRET": ""}) == [
        "STRIPE_WEBHOOK_SECRET is not set, but STRIPE_SECRET_KEY is: no Stripe "
        "notification could be verified, so nothing is marked paid."
    ]


def test_flitts_published_test_merchant_is_refused() -> None:
    problems = problems_with(
        {"FLITT_MERCHANT_ID": "1549901", "FLITT_SECRET_KEY": "test"}
    )

    assert [problem.split(" ", 1)[0] for problem in problems] == [
        "FLITT_MERCHANT_ID",
        "FLITT_SECRET_KEY",
    ]
    assert (
        problems_with({"FLITT_MERCHANT_ID": "1700001", "FLITT_SECRET_KEY": "s"}) == []
    )


@pytest.mark.parametrize(
    ("changes", "missing"),
    [
        ({"FLITT_MERCHANT_ID": "1700001"}, ["FLITT_SECRET_KEY"]),
        ({"FLITT_SECRET_KEY": "merchant-secret"}, ["FLITT_MERCHANT_ID"]),
        ({"META_APP_ID": "1234567890"}, ["META_APP_SECRET", "META_VERIFY_TOKEN"]),
        (
            {"WHATSAPP_SYSTEM_USER_TOKEN": "fake-system-user-token"},
            ["META_APP_SECRET", "META_VERIFY_TOKEN"],
        ),
        ({"ELEVENLABS_API_KEY": "fake-elevenlabs-key"}, ["ELEVENLABS_WEBHOOK_SECRET"]),
        ({"GOOGLE_OAUTH_CLIENT_ID": "client.apps"}, ["GOOGLE_OAUTH_CLIENT_SECRET"]),
    ],
)
def test_an_enabled_feature_needs_its_verification_secret(
    changes: dict[str, str], missing: list[str]
) -> None:
    problems = problems_with(changes)

    assert [problem.split(" ", 1)[0] for problem in problems] == missing


def test_meta_with_both_secrets_passes() -> None:
    assert (
        problems_with(
            {
                "META_APP_ID": "1234567890",
                "META_APP_SECRET": "fake-app-secret",
                "META_VERIFY_TOKEN": "fake-verify-token",
            }
        )
        == []
    )
