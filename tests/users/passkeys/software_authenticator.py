"""
A passkey authenticator in software, for tests: it creates a P-256
credential and answers registration and assertion options with real
WebAuthn data (`none` attestation, signed authenticator data), so the
server's checks run unchanged. `copy()` clones it, key and counter, as an
attacker who copied a security key would.
"""

import hashlib
import json
import secrets
from dataclasses import dataclass, field, replace
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url, encode_cbor

FLAG_USER_PRESENT: int = 0x01
FLAG_USER_VERIFIED: int = 0x04
FLAG_BACKUP_ELIGIBLE: int = 0x08
FLAG_BACKED_UP: int = 0x10
FLAG_ATTESTED_DATA: int = 0x40
COSE_ES256: int = -7

type JsonObject = dict[str, Any]


@dataclass
class SoftwareAuthenticator:
    """
    `counts_signatures`: a security key or platform authenticator with a
    counter (grows by one per signature); False: a synced passkey, which
    reports 0 every time.
    """

    origin: str
    private_key: ec.EllipticCurvePrivateKey = field(
        default_factory=lambda: ec.generate_private_key(ec.SECP256R1())
    )
    credential_id: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    sign_count: int = 0
    counts_signatures: bool = True
    is_synced: bool = False
    transports: tuple[str, ...] = ("internal", "hybrid")

    @property
    def credential_id_text(self) -> str:
        return bytes_to_base64url(self.credential_id)

    def copy(self) -> SoftwareAuthenticator:
        """A clone: the same key and credential, the counter where it stands."""

        return replace(self)

    def register(self, options: JsonObject, *, origin: str | None = None) -> JsonObject:
        """The `PublicKeyCredential` `navigator.credentials.create()` returns."""

        client_data: bytes = self._client_data(
            "webauthn.create", options["challenge"], origin
        )
        auth_data: bytes = self._authenticator_data(
            options["rp"]["id"], FLAG_ATTESTED_DATA, self._attested_credential()
        )
        attestation: bytes = encode_cbor(
            {"fmt": "none", "attStmt": {}, "authData": auth_data}
        )
        return {
            "id": self.credential_id_text,
            "raw_id": self.credential_id_text,
            "response": {
                "client_data_json": bytes_to_base64url(client_data),
                "attestation_object": bytes_to_base64url(attestation),
                "transports": list(self.transports),
            },
        }

    def sign(self, options: JsonObject, *, origin: str | None = None) -> JsonObject:
        """The `PublicKeyCredential` `navigator.credentials.get()` returns."""

        allowed: list[str] = [item["id"] for item in options["allow_credentials"]]
        assert self.credential_id_text in allowed, "not offered by the server"
        if self.counts_signatures:
            self.sign_count += 1
        client_data: bytes = self._client_data(
            "webauthn.get", options["challenge"], origin
        )
        auth_data: bytes = self._authenticator_data(options["rp_id"], 0, b"")
        signature: bytes = self.private_key.sign(
            auth_data + hashlib.sha256(client_data).digest(),
            ec.ECDSA(hashes.SHA256()),
        )
        return {
            "id": self.credential_id_text,
            "raw_id": self.credential_id_text,
            "response": {
                "client_data_json": bytes_to_base64url(client_data),
                "authenticator_data": bytes_to_base64url(auth_data),
                "signature": bytes_to_base64url(signature),
            },
        }

    def _client_data(self, kind: str, challenge: str, origin: str | None) -> bytes:
        # The challenge goes back exactly as the options carried it.
        assert base64url_to_bytes(challenge)
        return json.dumps(
            {
                "type": kind,
                "challenge": challenge,
                "origin": origin or self.origin,
                "crossOrigin": False,
            }
        ).encode()

    def _authenticator_data(self, rp_id: str, extra_flags: int, tail: bytes) -> bytes:
        flags: int = FLAG_USER_PRESENT | FLAG_USER_VERIFIED | extra_flags
        if self.is_synced:
            flags |= FLAG_BACKUP_ELIGIBLE | FLAG_BACKED_UP
        return (
            hashlib.sha256(rp_id.encode()).digest()
            + bytes([flags])
            + self.sign_count.to_bytes(4, "big")
            + tail
        )

    def _attested_credential(self) -> bytes:
        numbers = self.private_key.public_key().public_numbers()
        public_key: bytes = encode_cbor(
            {
                1: 2,
                3: COSE_ES256,
                -1: 1,
                -2: numbers.x.to_bytes(32, "big"),
                -3: numbers.y.to_bytes(32, "big"),
            }
        )
        return (
            bytes(16)
            + len(self.credential_id).to_bytes(2, "big")
            + self.credential_id
            + public_key
        )
