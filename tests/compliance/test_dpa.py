"""Accepting the data processing agreement and reading its text."""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.compliance import AcceptDpaCommand, DpaDocumentQuery
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.compliance.get_dpa_status_use_case import GetDpaStatusUseCase
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.compliance.business_with_staff import business_with_staff
from tests.users.accounts_phones import ISRAEL_MOBILE
from tests.users.accounts_testbed import build_accounts_testbed


def test_owner_accepts_the_current_agreement_version() -> None:
    testbed = build_accounts_testbed({"DPA_DOCUMENT_VERSION": "2026-10-01"})
    owner_id, staff_id, business = business_with_staff(testbed)

    before = testbed.get_dpa_status.run(
        BusinessQuery(user_id=staff_id, business_id=business.id)
    )
    accepted = testbed.accept_dpa.run(
        AcceptDpaCommand(
            user_id=owner_id,
            business_id=business.id,
            client_ip_address=ClientIpAddress("2001:db8::1"),
        )
    )
    after = testbed.get_dpa_status.run(
        BusinessQuery(user_id=staff_id, business_id=business.id)
    )

    assert before.is_current_version_accepted is False
    assert before.latest_acceptance is None
    assert before.current_document_version == "2026-10-01"
    assert before.document_url == "/v1/legal/dpa/2026-10-01"
    assert accepted.is_current_version_accepted is True
    assert after == accepted
    assert after.latest_acceptance is not None
    assert after.latest_acceptance.accepted_by == owner_id
    assert after.latest_acceptance.document_version == "2026-10-01"
    assert after.latest_acceptance.accepted_at == testbed.clock.now_microseconds()
    stored = testbed.dpa_acceptance_repo.list_by_business(business.id)
    assert [acceptance.document_version for acceptance in stored] == ["2026-10-01"]
    dpa_entries = [
        entry
        for entry in testbed.audit_log_repo.list_by_business(business.id)
        if entry.entity == "dpa_acceptance"
    ]
    assert len(dpa_entries) == 1
    assert dpa_entries[0].action is AuditAction.CREATE
    assert dpa_entries[0].ip_address == "2001:db8::1"


def test_new_agreement_version_needs_a_new_acceptance() -> None:
    testbed = build_accounts_testbed({"DPA_DOCUMENT_VERSION": "2026-10-01"})
    owner_id, _, business = business_with_staff(testbed)
    testbed.accept_dpa.run(AcceptDpaCommand(user_id=owner_id, business_id=business.id))
    newer_settings = assemble_app_settings({"DPA_DOCUMENT_VERSION": "2027-01-01"})
    status_with_new_version = GetDpaStatusUseCase(
        authorize_business_access=testbed.authorize_business_access,
        dpa_acceptance_repo=testbed.dpa_acceptance_repo,
        legal_document_registry=testbed.legal_document_registry,
        app_settings=newer_settings,
    ).run(BusinessQuery(user_id=owner_id, business_id=business.id))

    assert status_with_new_version.current_document_version == "2027-01-01"
    assert status_with_new_version.document_url is None
    assert status_with_new_version.is_current_version_accepted is False
    assert status_with_new_version.latest_acceptance is not None
    assert status_with_new_version.latest_acceptance.document_version == "2026-10-01"


def test_only_owners_accept_and_strangers_see_nothing() -> None:
    testbed = build_accounts_testbed()
    _, staff_id, business = business_with_staff(testbed)
    stranger = testbed.sign_in_with_phone(ISRAEL_MOBILE)

    with pytest.raises(AccessDeniedError):
        testbed.accept_dpa.run(
            AcceptDpaCommand(user_id=staff_id, business_id=business.id)
        )
    with pytest.raises(NotFoundError):
        testbed.get_dpa_status.run(
            BusinessQuery(user_id=stranger.user.id, business_id=business.id)
        )
    assert testbed.dpa_acceptance_repo.list_by_business(business.id) == []


def test_a_version_without_a_text_cannot_be_accepted() -> None:
    testbed = build_accounts_testbed({"DPA_DOCUMENT_VERSION": "2026-11-15"})
    owner_id, _, business = business_with_staff(testbed)

    status = testbed.get_dpa_status.run(
        BusinessQuery(user_id=owner_id, business_id=business.id)
    )
    with pytest.raises(ConflictError):
        testbed.accept_dpa.run(
            AcceptDpaCommand(user_id=owner_id, business_id=business.id)
        )

    assert status.document_url is None
    assert testbed.dpa_acceptance_repo.list_by_business(business.id) == []


@pytest.mark.parametrize(
    ("requested", "served"),
    [("ka", "ka"), ("ru-RU", "ru"), ("en", "en"), ("de", "en"), (None, "en")],
)
def test_the_agreement_text_is_served_in_the_language_or_english(
    requested: str | None,
    served: str,
) -> None:
    testbed = build_accounts_testbed()

    document = testbed.get_dpa_document.run(
        DpaDocumentQuery(
            version=DpaDocumentVersion("2026-10-01"),
            language=None if requested is None else LanguageTag(requested),
        )
    )

    assert document.language == served
    assert document.available_languages == ["en", "ka", "ru"]
    assert document.version == "2026-10-01"
    assert str(document.text).startswith(f"# {document.title}")
    assert "90" in str(document.text)


def test_every_translation_of_the_agreement_has_the_same_sections() -> None:
    testbed = build_accounts_testbed()
    version = DpaDocumentVersion("2026-10-01")

    outlines = {
        language: [
            line.split(".")[0]
            for line in str(
                testbed.get_dpa_document.run(
                    DpaDocumentQuery(version=version, language=LanguageTag(language))
                ).text
            ).splitlines()
            if line.startswith("## ")
        ]
        for language in ("en", "ru", "ka")
    }

    assert outlines["en"] == outlines["ru"] == outlines["ka"]
    assert len(outlines["en"]) == 15


def test_an_unknown_agreement_version_is_not_found() -> None:
    testbed = build_accounts_testbed()

    with pytest.raises(NotFoundError):
        testbed.get_dpa_document.run(
            DpaDocumentQuery(version=DpaDocumentVersion("1999-01-01"))
        )
