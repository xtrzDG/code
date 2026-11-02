"""
A change to how a person proves it is them is told to them at once: an
authenticator app or a passkey added or removed, and a new set of recovery
codes, each on their devices and by e-mail (SignInNoticeFacilitator), with
the address the change came from. A change nobody can be told about (an
unknown person) tells nobody and never fails the change.
"""

from collections.abc import Iterator
from typing import cast

import pytest

from app.facilitators.users.sign_in_notice_facilitator import SignInNoticeFacilitator
from app.schemas.constants.mfa import SecurityChange
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.security_change_notice_texts import (
    SecurityChangeNoticeTexts,
)
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import CABINET_ORIGIN, E2E_ENVIRONMENT
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE, sign_in_and_create_restaurant
from tests.e2e.workshop_container import replace_provider
from tests.foundation.support_access_builders import RecordingSignInNotices
from tests.operations.fakes import FakeLocalizedTextResolver
from tests.users.mfa.mfa_api import set_up_authenticator
from tests.users.passkeys.passkey_api import add_passkey, new_authenticator

CAFE_IP: str = "203.0.113.7"


@pytest.fixture
def noticed() -> RecordingSignInNotices:
    return RecordingSignInNotices()


@pytest.fixture
def workshop(noticed: RecordingSignInNotices) -> Iterator[Workshop]:
    workshop = start_workshop(
        {**E2E_ENVIRONMENT, "CABINET_BASE_URL": CABINET_ORIGIN},
        prepare=lambda container: replace_provider(
            container.facilitators.sign_in_notice_facilitator,
            cast(SignInNoticeFacilitator, noticed),
        ),
    )
    with workshop.client:
        yield workshop


def test_every_second_factor_change_is_told(
    workshop: Workshop, noticed: RecordingSignInNotices
) -> None:
    token, user_id, _ = sign_in_and_create_restaurant(workshop)
    token, _ = set_up_authenticator(workshop, token, GEORGIAN_OWNER_PHONE)
    renewed = workshop.client.post("/v1/me/mfa/recovery-codes", headers=bearer(token))
    added = add_passkey(workshop, token, new_authenticator())
    removed_passkey = workshop.client.delete(
        f"/v1/me/passkeys/{added.json()['passkey']['id']}", headers=bearer(token)
    )
    removed_app = workshop.client.delete("/v1/me/mfa/totp", headers=bearer(token))

    assert renewed.status_code == 200, renewed.text
    assert added.status_code == 201, added.text
    assert removed_passkey.status_code == 204
    assert removed_app.status_code == 204
    assert noticed.changes == [
        (UserId(user_id), SecurityChange.TOTP_ADDED),
        (UserId(user_id), SecurityChange.RECOVERY_CODES_RENEWED),
        (UserId(user_id), SecurityChange.PASSKEY_ADDED),
        (UserId(user_id), SecurityChange.PASSKEY_REMOVED),
        (UserId(user_id), SecurityChange.TOTP_REMOVED),
    ]


def test_a_refused_change_tells_nobody(
    workshop: Workshop, noticed: RecordingSignInNotices
) -> None:
    token, _, _ = sign_in_and_create_restaurant(workshop)

    # Nothing to remove and no second factor to renew codes for.
    removed = workshop.client.delete("/v1/me/mfa/totp", headers=bearer(token))
    renewed = workshop.client.post("/v1/me/mfa/recovery-codes", headers=bearer(token))

    assert removed.status_code == 404
    assert renewed.status_code == 409
    assert noticed.changes == []


@pytest.mark.parametrize("change", list(SecurityChange))
def test_each_change_has_its_own_words_in_english_and_italian(
    change: SecurityChange,
) -> None:
    texts = SecurityChangeNoticeTexts(
        FakeLocalizedTextResolver(), change, ClientIpAddress(CAFE_IP)
    )

    english = texts.brief(LanguageTag("en"))
    italian = texts.brief(LanguageTag("it"))

    assert str(english.title) == "Your sign-in protection changed"
    assert str(italian.title) == "La protezione del tuo accesso è cambiata"
    for brief in (english, italian):
        assert f"({CAFE_IP})" in str(brief.detail)
        assert "{address}" not in str(brief.detail)
    assert "Account → Security" in str(english.detail)
    assert "Account → Sicurezza" in str(italian.detail)
    others = [
        str(
            SecurityChangeNoticeTexts(FakeLocalizedTextResolver(), other, None)
            .brief(LanguageTag("en"))
            .detail
        )
        for other in SecurityChange
        if other is not change
    ]
    assert str(english.detail) not in others
    assert texts.detailed(LanguageTag("en")).startswith(str(english.title))
