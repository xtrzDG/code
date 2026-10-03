"""The age v1 format of the backup archives: round trips and tampering."""

import io
import os

import pytest

from app.schemas.typings.backups.constrained_strings import AgeIdentity, AgeRecipient
from app.utilities.security.age.age_header import (
    AgeFormatError,
    decode_base64,
    wrap_body,
)
from app.utilities.security.age.age_keys import (
    AgeKeyError,
    generate_identity,
    read_identity,
    read_recipient,
    recipient_of,
)
from app.utilities.security.age.age_stream import (
    CHUNK_SIZE,
    decrypt_stream,
    encrypt_stream,
)
from app.utilities.security.age.bech32 import Bech32Error, bech32_decode

# A key pair written by `age-keygen` (a test key, it protects nothing).
KNOWN_IDENTITY: str = (
    "AGE-SECRET-KEY-1" + "8LC4LTDCNR5ZTWL0DMFCANWAC05KLX9L0KHCY4LG053SRU0SW9QQTZEV24"
)
KNOWN_RECIPIENT: str = "age172lakmdn6gj087zpss7rre4zen4yam6qgdk42mgqaat5mqfe2arskq34yv"


def encrypt(plaintext: bytes, *identities: AgeIdentity) -> bytes:
    archive = io.BytesIO()
    encrypt_stream(
        io.BytesIO(plaintext),
        archive,
        [read_recipient(recipient_of(identity)) for identity in identities],
    )
    return archive.getvalue()


def decrypt(archive: bytes, identity: AgeIdentity) -> bytes:
    plaintext = io.BytesIO()
    decrypt_stream(io.BytesIO(archive), plaintext, read_identity(identity))
    return plaintext.getvalue()


@pytest.mark.parametrize(
    "size",
    [0, 1, CHUNK_SIZE - 1, CHUNK_SIZE, CHUNK_SIZE + 1, 3 * CHUNK_SIZE, 200_001],
)
def test_every_size_round_trips(size: int) -> None:
    identity = generate_identity()
    plaintext = os.urandom(size)

    assert decrypt(encrypt(plaintext, identity), identity) == plaintext


def test_every_recipient_opens_the_archive_and_others_do_not() -> None:
    drill, escrow, stranger = (generate_identity() for _ in range(3))
    archive = encrypt(b"pg_dump output", drill, escrow)

    assert decrypt(archive, drill) == b"pg_dump output"
    assert decrypt(archive, escrow) == b"pg_dump output"
    with pytest.raises(AgeFormatError, match="not encrypted to this identity"):
        decrypt(archive, stranger)


def test_the_header_names_x25519_stanzas_and_hides_the_plaintext() -> None:
    identity = generate_identity()
    archive = encrypt(b"secret customer data", identity)

    assert archive.startswith(b"age-encryption.org/v1\n-> X25519 ")
    assert b"secret customer data" not in archive


def test_a_changed_header_fails_its_mac() -> None:
    identity, other = generate_identity(), generate_identity()
    archive = encrypt(b"data", identity, other)
    first_stanza_end = archive.index(b"\n-> X25519 ", 1)
    # Drop the other recipient's stanza: the MAC covers the whole header.
    second_stanza = archive.index(b"\n-> X25519 ", first_stanza_end + 1)
    mac_line = archive.index(b"\n---", second_stanza)
    trimmed = archive[:second_stanza] + archive[mac_line:]

    with pytest.raises(AgeFormatError, match="MAC"):
        decrypt(trimmed, identity)


@pytest.mark.parametrize("cut", [1, 16, CHUNK_SIZE])
def test_a_cut_off_archive_does_not_open(cut: int) -> None:
    identity = generate_identity()
    archive = encrypt(os.urandom(2 * CHUNK_SIZE + 10), identity)

    with pytest.raises(AgeFormatError):
        decrypt(archive[:-cut], identity)


def test_a_flipped_payload_bit_does_not_open() -> None:
    identity = generate_identity()
    archive = bytearray(encrypt(os.urandom(CHUNK_SIZE * 2), identity))
    archive[-CHUNK_SIZE] ^= 0x01

    with pytest.raises(AgeFormatError, match="changed or cut off"):
        decrypt(bytes(archive), identity)


def test_an_extended_archive_does_not_open() -> None:
    identity = generate_identity()
    archive = encrypt(os.urandom(CHUNK_SIZE), identity)

    with pytest.raises(AgeFormatError):
        decrypt(archive + os.urandom(40), identity)


def test_other_files_are_refused() -> None:
    identity = generate_identity()

    with pytest.raises(AgeFormatError, match="not an age v1 file"):
        decrypt(b"PGDMP\x01\x0f\x00", identity)
    with pytest.raises(AgeFormatError, match="cut off"):
        decrypt(b"age-encryption.org/v1\n-> X25519 AAAA", identity)
    with pytest.raises(AgeFormatError, match="no stanza"):
        decrypt(b"age-encryption.org/v1\n--- AAAA\n", identity)


def test_base64_must_be_canonical_and_unpadded() -> None:
    assert decode_base64(b"YWdl") == b"age"
    with pytest.raises(AgeFormatError, match="non-canonical"):
        decode_base64(b"YWd")  # its last character carries stray bits
    with pytest.raises(AgeFormatError, match="invalid base64"):
        decode_base64(b"YW=l")


def test_stanza_bodies_wrap_at_64_columns() -> None:
    assert wrap_body(b"a" * 43) == [b"a" * 43]
    assert wrap_body(b"a" * 64) == [b"a" * 64, b""]
    assert wrap_body(b"a" * 70) == [b"a" * 64, b"a" * 6]


def test_known_age_keygen_keys_are_read() -> None:
    identity = AgeIdentity(KNOWN_IDENTITY)

    assert recipient_of(identity) == AgeRecipient(KNOWN_RECIPIENT)
    assert str(generate_identity()).startswith("AGE-SECRET-KEY-1")


def test_damaged_keys_are_refused() -> None:
    damaged: str = KNOWN_RECIPIENT[:-1] + ("q" if KNOWN_RECIPIENT[-1] != "q" else "p")

    with pytest.raises(AgeKeyError, match="checksum"):
        read_recipient(AgeRecipient(damaged))
    with pytest.raises(Bech32Error, match="mixes upper and lower"):
        bech32_decode("Age1" + KNOWN_RECIPIENT[4:], "age")
    with pytest.raises(Bech32Error, match="Expected a key"):
        bech32_decode(KNOWN_RECIPIENT, "age-secret-key-")
    with pytest.raises(Bech32Error, match="no separator"):
        bech32_decode("agexyz", "age")
    with pytest.raises(Bech32Error, match="outside its alphabet"):
        bech32_decode("age1bbbbbbbbbb", "age")
