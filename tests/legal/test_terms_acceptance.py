"""
Signing in accepts the terms the sign-in page showed: the code check stores
that version and when on the account; a version this build has no text of,
or one not in force yet, is not recorded and never blocks the sign-in; an
older page never takes a newer acceptance back.
"""

from pathlib import Path
from typing import Any

from typed_time_provider import Microseconds

from app.registries.legal.legal_text_registry import LegalTextRegistry
from app.schemas.typings.legal.constrained_strings import LegalDocumentVersion
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.users.otp_login.terms_acceptance import record_terms_acceptance
from tests.legal.legal_world import moment, user
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

TERMS = "2026-10-05"
EMAIL = "owner@example.com"


def accounts_on(day: str) -> AccountsTestbed:
    testbed = build_accounts_testbed()
    testbed.clock.nanoseconds = int(moment(day)) * 1_000
    return testbed


def sign_in(testbed: AccountsTestbed, shown: str | None) -> dict[str, Any]:
    client = testbed.build_http_client()
    challenge = client.post("/v1/auth/otp/start", json={"email": EMAIL}).json()
    body: dict[str, Any] = {
        "challenge_id": challenge["challenge_id"],
        "code": testbed.otp_delivery.last_code(),
    }
    if shown is not None:
        body["accepted_terms_version"] = shown
    response = client.post("/v1/auth/otp/verify", json=body)
    assert response.status_code == 200, response.text
    login: dict[str, Any] = response.json()
    return login


def stored_terms(testbed: AccountsTestbed) -> tuple[str | None, int | None]:
    account = testbed.user_repo.find_by_email(EmailAddress(EMAIL))
    assert account is not None
    version = account.accepted_terms_version
    accepted_at = account.terms_accepted_at
    return (
        None if version is None else str(version),
        None if accepted_at is None else int(accepted_at),
    )


def test_continuing_with_the_code_accepts_the_terms_shown() -> None:
    testbed = accounts_on("2026-10-06")

    login = sign_in(testbed, TERMS)

    assert login["user"]["accepted_terms_version"] == TERMS
    assert stored_terms(testbed) == (TERMS, int(moment("2026-10-06")))


def test_the_sign_in_page_names_the_versions_in_force() -> None:
    client = accounts_on("2026-10-06").build_http_client()

    options = client.get("/v1/auth/login-options").json()

    assert options["terms_version"] == TERMS
    assert options["privacy_version"] == TERMS


def test_without_the_line_nothing_is_recorded() -> None:
    testbed = accounts_on("2026-10-06")

    login = sign_in(testbed, None)

    assert login["user"]["accepted_terms_version"] is None
    assert stored_terms(testbed) == (None, None)


def test_terms_unknown_or_not_in_force_do_not_block_the_sign_in() -> None:
    unknown = accounts_on("2026-10-06")
    early = accounts_on("2026-10-04")

    sign_in(unknown, "2026-10-01")
    sign_in(early, TERMS)

    assert stored_terms(unknown) == (None, None)
    assert stored_terms(early) == (None, None)


def test_the_next_sign_in_accepts_a_newer_version_but_never_an_older_one(
    tmp_path: Path,
) -> None:
    (tmp_path / "terms-2026-10-05.en.md").write_text("# Terms\n", "utf-8")
    (tmp_path / "terms-2026-12-01.en.md").write_text("# Terms\n", "utf-8")
    registry = LegalTextRegistry(tmp_path)
    person = user("en", email=EMAIL)
    december: Microseconds = moment("2026-12-02")

    record_terms_acceptance(person, LegalDocumentVersion(TERMS), registry, december)
    record_terms_acceptance(
        person, LegalDocumentVersion("2026-12-01"), registry, december
    )
    record_terms_acceptance(person, LegalDocumentVersion(TERMS), registry, december)

    assert person.accepted_terms_version == LegalDocumentVersion("2026-12-01")
    assert person.terms_accepted_at == december
