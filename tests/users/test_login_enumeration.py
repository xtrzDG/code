"""
A login code request never tells whether a phone or e-mail belongs to an
account (ABUSE-01): a returning owner's destination and a stranger's get
the same status and the same body, apart from the challenge's own id and
the destination they named, with the bot check off and on, with and
without its token.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.users.accounts_phones import GEORGIA_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed
from tests.users.login_protection_fakes import PASSING_TOKEN

type JsonObject = dict[str, Any]

UNKNOWN_GEORGIAN_MOBILE: str = "+995 555 98 76 54"
OWNER_EMAIL: str = "owner@salobie.example"
UNKNOWN_EMAIL: str = "stranger@salobie.example"
RESEND_WAIT_SECONDS: int = 31
# What differs because the destinations differ, not because one is known.
OWN_FIELDS: frozenset[str] = frozenset(
    {
        "challenge_id",
        "masked_destination",
        "phone_number",
        "international_phone_number",
    }
)


def with_returning_owner(is_check_on: bool) -> tuple[AccountsTestbed, TestClient]:
    testbed = build_accounts_testbed()
    testbed.sign_in_with_phone(GEORGIA_MOBILE)
    testbed.sign_in_with_email(OWNER_EMAIL)
    testbed.clock.advance(RESEND_WAIT_SECONDS)
    if is_check_on:
        testbed.bot_check.turn_on()
    return testbed, testbed.build_http_client()


def ask(client: TestClient, body: JsonObject, address: str) -> tuple[int, JsonObject]:
    answer = client.post(
        "/v1/auth/otp/start", json=body, headers={"X-Forwarded-For": address}
    )
    shown: JsonObject = {
        key: value for key, value in answer.json().items() if key not in OWN_FIELDS
    }
    return answer.status_code, shown


@pytest.mark.parametrize("is_check_on", [False, True])
@pytest.mark.parametrize("with_token", [False, True])
@pytest.mark.parametrize(
    ("field", "known", "unknown"),
    [
        ("phone_number", GEORGIA_MOBILE, UNKNOWN_GEORGIAN_MOBILE),
        ("email", OWNER_EMAIL, UNKNOWN_EMAIL),
    ],
)
def test_a_known_and_an_unknown_destination_get_the_same_answer(
    is_check_on: bool, with_token: bool, field: str, known: str, unknown: str
) -> None:
    testbed, client = with_returning_owner(is_check_on)
    token: JsonObject = {"turnstile_token": str(PASSING_TOKEN)} if with_token else {}

    # Each from its own quiet address: the address's history is not compared.
    known_answer = ask(client, {field: known, **token}, "198.51.100.21")
    unknown_answer = ask(client, {field: unknown, **token}, "198.51.100.22")

    assert known_answer == unknown_answer
    assert known_answer[0] in {200, 403}
    sent_both: bool = known_answer[0] == 200
    assert len(testbed.otp_delivery.deliveries) == 2 + (2 if sent_both else 0)


def test_with_the_check_on_a_phone_without_a_token_is_refused_alike() -> None:
    _, client = with_returning_owner(is_check_on=True)

    known_status, known_body = ask(
        client, {"phone_number": GEORGIA_MOBILE}, "198.51.100.31"
    )
    unknown_status, unknown_body = ask(
        client, {"phone_number": UNKNOWN_GEORGIAN_MOBILE}, "198.51.100.32"
    )

    assert known_status == unknown_status == 403
    assert known_body == unknown_body
    assert [reason["code"] for reason in known_body["reasons"]] == [
        "challenge_required"
    ]
