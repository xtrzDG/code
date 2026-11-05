"""
Login code hashes are keyed with the platform's key ring, not with the
(non-secret) challenge id alone: the database without the key cannot test
codes offline. A rotation keeps recent codes working; challenges written
before the change are read the old way until they expire.
"""

import hashlib
import hmac
import json

from typed_time_provider import Microseconds

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.schemas.typings.users.strings import OtpCodeHash
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.security.one_time_codes import (
    hash_otp_code,
    hash_otp_code_by_challenge,
    is_otp_code_matching,
    otp_hash_keys,
)

OLD_KEY: str = "old-login-code-test-key-00000000000"  # gitleaks:allow
NEW_KEY: str = "new-login-code-test-key-00000000000"  # gitleaks:allow
CODE: OtpCode = OtpCode("042317")


def settings_with(keys: str | None) -> AppSettings:
    return assemble_app_settings({} if keys is None else {"ENCRYPTION_KEYS": keys})


def challenge_of(
    challenge_id: OtpChallengeId, code_hash: str, is_keyed: bool
) -> OtpChallengeDocument:
    return OtpChallengeDocument(
        id=challenge_id,
        login_method=LoginMethod.PHONE,
        phone_number=E164PhoneNumber("+995555123456"),
        delivery_channel=OtpDeliveryChannel.SMS,
        locale=LanguageTag("en"),
        code_hash=OtpCodeHash(code_hash),
        expires_at=Microseconds(10),
        is_code_hash_server_keyed=is_keyed,
        created_at=Microseconds(1),
        updated_at=Microseconds(1),
    )


def test_the_hash_depends_on_the_server_key_and_the_challenge() -> None:
    first, second = OtpChallengeId(), OtpChallengeId()
    key = otp_hash_keys(settings_with(NEW_KEY))[0]
    other_key = otp_hash_keys(settings_with(OLD_KEY))[0]

    stored = hash_otp_code(key, first, CODE)

    assert stored == hash_otp_code(key, first, CODE)
    assert stored != hash_otp_code(key, second, CODE)
    assert stored != hash_otp_code(other_key, first, CODE)
    # Knowing the challenge id is not enough to test a code any more.
    assert str(stored) != hash_otp_code_by_challenge(first, CODE)
    assert (
        str(stored)
        != hmac.new(str(first).encode(), str(CODE).encode(), hashlib.sha256).hexdigest()
    )
    assert "042317" not in str(stored)
    assert len(str(stored)) == 64


def test_a_code_matches_only_its_own_challenge_and_code() -> None:
    challenge_id = OtpChallengeId()
    keys = otp_hash_keys(settings_with(NEW_KEY))
    challenge = challenge_of(
        challenge_id, str(hash_otp_code(keys[0], challenge_id, CODE)), True
    )

    assert is_otp_code_matching(challenge, CODE, keys) is True
    assert is_otp_code_matching(challenge, OtpCode("042318"), keys) is False
    other = challenge.model_copy(update={"id": OtpChallengeId()})
    assert is_otp_code_matching(other, CODE, keys) is False


def test_a_code_hashed_before_a_key_rotation_still_matches() -> None:
    challenge_id = OtpChallengeId()
    before = otp_hash_keys(settings_with(OLD_KEY))
    after = otp_hash_keys(settings_with(f"{NEW_KEY},{OLD_KEY}"))
    challenge = challenge_of(
        challenge_id, str(hash_otp_code(before[0], challenge_id, CODE)), True
    )

    assert after[0] != before[0]
    assert is_otp_code_matching(challenge, CODE, after) is True
    # Without the old key in the ring it is gone.
    assert (
        is_otp_code_matching(challenge, CODE, otp_hash_keys(settings_with(NEW_KEY)))
        is False
    )


def test_development_without_a_key_still_hashes_with_a_fixed_key() -> None:
    keys = otp_hash_keys(settings_with(None))

    assert len(keys) == 1
    assert keys == otp_hash_keys(settings_with(None))
    assert keys[0] != otp_hash_keys(settings_with(NEW_KEY))[0]


def test_a_challenge_from_before_the_keyed_hash_is_read_the_old_way() -> None:
    challenge_id = OtpChallengeId()
    keys = otp_hash_keys(settings_with(NEW_KEY))
    legacy = challenge_of(
        challenge_id, hash_otp_code_by_challenge(challenge_id, CODE), False
    )

    assert is_otp_code_matching(legacy, CODE, keys) is True
    assert is_otp_code_matching(legacy, OtpCode("000000"), keys) is False
    # A keyed challenge never falls back to the id-keyed hash.
    flagged = legacy.model_copy(update={"is_code_hash_server_keyed": True})
    assert is_otp_code_matching(flagged, CODE, keys) is False


def test_a_stored_version_two_challenge_reads_as_not_keyed() -> None:
    stored = challenge_of(OtpChallengeId(), "0" * 64, False).model_dump(mode="json")
    stored.pop("is_code_hash_server_keyed")
    stored["schema_version"] = "2"

    read = OtpChallengeDocument.model_validate_json(json.dumps(stored))

    assert read.is_code_hash_server_keyed is False
