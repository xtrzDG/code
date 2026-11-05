"""Web Push encryption against RFC 8291 and the VAPID token of RFC 8292."""

import json

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from app.clients.webpush.push_encryption import (
    MAX_PLAINTEXT_LENGTH,
    decode_base64url,
    encode_base64url,
    encrypt_push_payload,
    new_salt,
    new_sender_key,
    public_key_bytes,
)
from app.clients.webpush.vapid import (
    check_vapid_key_pair,
    load_vapid_private_key,
    push_service_origin,
    sign_vapid_token,
    vapid_authorization,
)

# RFC 8291, appendix A.
PLAINTEXT: bytes = b"When I grow up, I want to be a watermelon"
SENDER_PRIVATE: str = "yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"
SENDER_PUBLIC: str = (
    "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8w"
    "EqKK6PBru3jl7A8"
)
RECEIVER_PUBLIC: str = (
    "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZ"
    "GH6SRpkNtoIAiw4"
)
AUTH_SECRET: str = "BTBZMqHH6r4Tts7J_aSIgg"
SALT: str = "DGv6ra1nlYgDCS1FRnbzlw"
EXPECTED_BODY: str = (
    "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIg"
    "Dll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVB"
    "St2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN"
)


def test_the_rfc_8291_example_encrypts_to_the_published_body() -> None:
    sender = load_vapid_private_key(SENDER_PRIVATE)

    body = encrypt_push_payload(
        PLAINTEXT,
        decode_base64url(RECEIVER_PUBLIC),
        decode_base64url(AUTH_SECRET),
        sender,
        decode_base64url(SALT),
    )

    assert encode_base64url(body) == EXPECTED_BODY
    assert encode_base64url(public_key_bytes(sender.public_key())) == SENDER_PUBLIC


def test_fresh_keys_and_salts_differ_each_time() -> None:
    first, second = new_sender_key(), new_sender_key()

    assert public_key_bytes(first.public_key()) != public_key_bytes(second.public_key())
    assert len(new_salt()) == 16 and new_salt() != new_salt()
    assert decode_base64url(AUTH_SECRET + "==") == decode_base64url(AUTH_SECRET)


@pytest.mark.parametrize(
    ("payload", "receiver", "auth", "salt"),
    [
        (b"x" * (MAX_PLAINTEXT_LENGTH + 1), RECEIVER_PUBLIC, AUTH_SECRET, SALT),
        (PLAINTEXT, RECEIVER_PUBLIC, "c2hvcnQ", SALT),
        (PLAINTEXT, RECEIVER_PUBLIC, AUTH_SECRET, "c2hvcnQ"),
        (PLAINTEXT, AUTH_SECRET, AUTH_SECRET, SALT),
    ],
)
def test_unusable_inputs_are_refused(
    payload: bytes, receiver: str, auth: str, salt: str
) -> None:
    with pytest.raises(ValueError):
        encrypt_push_payload(
            payload,
            decode_base64url(receiver),
            decode_base64url(auth),
            new_sender_key(),
            decode_base64url(salt),
        )


def test_the_vapid_token_is_an_es256_jwt_for_the_push_service() -> None:
    key = load_vapid_private_key(SENDER_PRIVATE)
    audience = push_service_origin("https://fcm.googleapis.com/fcm/send/abc?x=1")

    token = sign_vapid_token(key, audience, "mailto:ops@example.com", 1_790_000_000)

    header, claims, signature = token.split(".")
    assert json.loads(decode_base64url(header)) == {"typ": "JWT", "alg": "ES256"}
    assert json.loads(decode_base64url(claims)) == {
        "aud": "https://fcm.googleapis.com",
        "exp": 1_790_000_000 + 12 * 60 * 60,
        "sub": "mailto:ops@example.com",
    }
    raw = decode_base64url(signature)
    der = encode_dss_signature(
        int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")
    )
    key.public_key().verify(
        der, f"{header}.{claims}".encode(), ec.ECDSA(hashes.SHA256())
    )
    with pytest.raises(InvalidSignature):
        key.public_key().verify(
            der, f"{header}.{claims}x".encode(), ec.ECDSA(hashes.SHA256())
        )
    assert vapid_authorization(token, SENDER_PUBLIC + "=") == (
        f"vapid t={token}, k={SENDER_PUBLIC}"
    )


def test_a_mismatched_or_malformed_key_pair_is_refused() -> None:
    key = load_vapid_private_key(SENDER_PRIVATE)
    check_vapid_key_pair(key, SENDER_PUBLIC)

    with pytest.raises(ValueError, match="does not belong"):
        check_vapid_key_pair(key, RECEIVER_PUBLIC)

    with pytest.raises(ValueError, match="32 bytes"):
        load_vapid_private_key(AUTH_SECRET)
