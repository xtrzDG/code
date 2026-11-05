"""
The signature a receiver checks: HMAC-SHA256 of `<t>.<body>` with the
endpoint's secret, refused when the body, the secret or the time differ.
"""

from app.schemas.typings.integrations.constrained_strings import (
    WebhookSigningSecret,
)
from app.schemas.typings.integrations.strings import WebhookPayloadJson
from app.utilities.integrations.integration_secrets import new_signing_secret
from app.utilities.integrations.webhook_signatures import sign_webhook_body
from tests.integrations.webhook_receivers import is_valid_signature

SECRET: WebhookSigningSecret = WebhookSigningSecret(
    "whsec_" + "a" * 43  # gitleaks:allow
)
BODY: WebhookPayloadJson = WebhookPayloadJson('{"id":"event_1","type":"lead.created"}')
SIGNED_AT: int = 1_790_000_000


def test_a_receiver_accepts_the_signature_of_the_body() -> None:
    header = sign_webhook_body(SECRET, SIGNED_AT, BODY)

    assert str(header).startswith(f"t={SIGNED_AT},v1=")
    assert is_valid_signature(str(SECRET), str(header), str(BODY), SIGNED_AT + 10)


def test_a_changed_body_or_another_secret_is_refused() -> None:
    header = str(sign_webhook_body(SECRET, SIGNED_AT, BODY))
    other_secret, _ = new_signing_secret()

    assert not is_valid_signature(str(SECRET), header, str(BODY) + " ", SIGNED_AT)
    assert not is_valid_signature(str(other_secret), header, str(BODY), SIGNED_AT)


def test_an_old_signature_is_a_replay() -> None:
    header = str(sign_webhook_body(SECRET, SIGNED_AT, BODY))

    assert is_valid_signature(str(SECRET), header, str(BODY), SIGNED_AT + 300)
    assert not is_valid_signature(str(SECRET), header, str(BODY), SIGNED_AT + 301)


def test_a_malformed_header_is_refused() -> None:
    for header in ("", "t=abc,v1=00", f"t={SIGNED_AT}", "v1=00"):
        assert not is_valid_signature(str(SECRET), header, str(BODY), SIGNED_AT)


def test_signing_secrets_are_random_and_hinted_by_their_end() -> None:
    first, first_hint = new_signing_secret()
    second, _ = new_signing_secret()

    assert first != second
    assert str(first).startswith("whsec_")
    assert str(first).endswith(str(first_hint))
