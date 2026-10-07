"""
A new dated version of the data processing agreement: the business keeps the
version an owner accepted, owners who accepted an earlier one are asked to
accept the new one within 30 days of its date, and the go-live gates hold
until they do.
"""

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.compliance import AcceptDpaCommand, DpaStatusView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.compliance.get_dpa_status_use_case import GetDpaStatusUseCase
from app.use_cases.shared.dpa_acceptance import is_dpa_version_accepted
from app.utilities.compliance.dpa_versions import acceptance_due_on
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.compliance.business_with_staff import business_with_staff
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

PREVIOUS: str = "2026-10-01"
CURRENT: str = "2026-10-06"


def status_under(
    testbed: AccountsTestbed, version: str, user_id: UserId, business_id: BusinessId
) -> DpaStatusView:
    return GetDpaStatusUseCase(
        authorize_business_access=testbed.authorize_business_access,
        dpa_acceptance_repo=testbed.dpa_acceptance_repo,
        legal_document_registry=testbed.legal_document_registry,
        app_settings=assemble_app_settings({"DPA_DOCUMENT_VERSION": version}),
    ).run(BusinessQuery(user_id=user_id, business_id=business_id))


def test_the_business_remembers_the_version_an_owner_accepted() -> None:
    testbed = build_accounts_testbed({"DPA_DOCUMENT_VERSION": CURRENT})
    owner_id, _, business = business_with_staff(testbed)

    accepted = testbed.accept_dpa.run(
        AcceptDpaCommand(user_id=owner_id, business_id=business.id)
    )

    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert stored.dpa_version_accepted == CURRENT
    assert accepted.is_current_version_accepted is True
    assert accepted.needs_reacceptance is False
    assert accepted.acceptance_due_on is None


def test_owners_of_an_earlier_version_accept_the_new_one_within_30_days() -> None:
    testbed = build_accounts_testbed({"DPA_DOCUMENT_VERSION": PREVIOUS})
    owner_id, staff_id, business = business_with_staff(testbed)
    testbed.accept_dpa.run(AcceptDpaCommand(user_id=owner_id, business_id=business.id))

    status = status_under(testbed, CURRENT, staff_id, business.id)

    assert status.current_document_version == CURRENT
    assert status.document_url == f"/v1/legal/dpa/{CURRENT}"
    assert status.is_current_version_accepted is False
    assert status.needs_reacceptance is True
    assert status.acceptance_due_on == "2026-11-05"
    assert status.latest_acceptance is not None
    assert status.latest_acceptance.document_version == PREVIOUS


def test_a_business_that_never_accepted_is_not_asked_to_accept_again() -> None:
    testbed = build_accounts_testbed({"DPA_DOCUMENT_VERSION": CURRENT})
    owner_id, _, business = business_with_staff(testbed)

    status = testbed.get_dpa_status.run(
        BusinessQuery(user_id=owner_id, business_id=business.id)
    )

    assert status.is_current_version_accepted is False
    assert status.needs_reacceptance is False
    assert status.acceptance_due_on is None


def test_acceptances_from_before_the_business_field_still_count() -> None:
    testbed = build_accounts_testbed({"DPA_DOCUMENT_VERSION": CURRENT})
    owner_id, _, business = business_with_staff(testbed)
    testbed.accept_dpa.run(AcceptDpaCommand(user_id=owner_id, business_id=business.id))

    def forget(stored: BusinessDocument) -> None:
        stored.dpa_version_accepted = None

    legacy = testbed.business_repo.update(business.id, forget)
    version = DpaDocumentVersion(CURRENT)

    assert legacy.dpa_version_accepted is None
    assert is_dpa_version_accepted(legacy, version, testbed.dpa_acceptance_repo)
    assert not is_dpa_version_accepted(
        legacy, DpaDocumentVersion("2027-01-01"), testbed.dpa_acceptance_repo
    )


def test_only_dated_versions_have_a_deadline() -> None:
    assert acceptance_due_on(DpaDocumentVersion("2026-12-15")) == "2027-01-14"
    assert acceptance_due_on(DpaDocumentVersion("v2")) is None
    assert acceptance_due_on(DpaDocumentVersion("2026-02-30")) is None
