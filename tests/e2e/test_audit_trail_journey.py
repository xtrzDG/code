"""
The audit trail on the real application: sign-in failures and sign-outs
land in the platform's hash chain, the daily check verifies every chain,
the owner sees their business's chain on the Audit tab and only platform
admins read the platform's entries.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from app.schemas.dto.jobs import JobTick
from app.schemas.typings.platform.constrained_strings import JobName
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import sign_in_and_create_restaurant

type JsonObject = dict[str, Any]

STRANGER_PHONE: str = "+995 555 00 11 33"
ADMIN_LOG_URL: str = "/v1/admin/audit-log"
# A second code to the same phone waits half a minute.
SEND_PAUSE_SECONDS: int = 31


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    running = start_workshop()
    with running.client:
        yield running


def fail_one_code(workshop: Workshop, phone: str) -> None:
    started = workshop.client.post("/v1/auth/otp/start", json={"phone_number": phone})
    assert started.status_code == 200, started.text
    code = str(workshop.otp.codes[-1].code)
    wrong = "000000" if code != "000000" else "111111"
    refused = workshop.client.post(
        "/v1/auth/otp/verify",
        json={"challenge_id": started.json()["challenge_id"], "code": wrong},
    )
    assert refused.status_code == 401, refused.text


def verify_chains(workshop: Workshop) -> None:
    workshop.container.operators.audit_trail.verify_audit_chains_operator().operate(
        JobTick(
            job_name=JobName("verify_audit_chain"),
            scheduled_at=(
                workshop.container.time_provider.microsecond_wall_clock().now_unix()
            ),
        )
    )


def test_security_events_and_chain_checks_reach_owner_and_admin(
    workshop: Workshop,
) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    owner = bearer(token)
    chain_url = f"/v1/businesses/{business_id}/audit-log/chain"
    accepted = workshop.client.post(
        f"/v1/businesses/{business_id}/dpa", json={}, headers=owner
    )
    assert accepted.status_code == 201, accepted.text  # An audited operation.
    fail_one_code(workshop, STRANGER_PHONE)
    workshop.clock.advance(SEND_PAUSE_SECONDS)
    stranger_token, _ = workshop.sign_in_with_phone(STRANGER_PHONE)
    signed_out = workshop.client.post("/v1/auth/logout", headers=bearer(stranger_token))
    assert signed_out.status_code == 204

    before = workshop.client.get(chain_url, headers=owner)
    verify_chains(workshop)
    after = workshop.client.get(chain_url, headers=owner)

    assert before.status_code == 200, before.text
    assert before.json()["status"] is None
    assert after.json()["status"] == "intact"
    assert after.json()["verified_through_position"] >= 1
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    admin = bearer(admin_token)
    log = workshop.client.get(ADMIN_LOG_URL, headers=admin)
    failed = workshop.client.get(
        ADMIN_LOG_URL, params={"security_event": "login_failed"}, headers=admin
    )
    chains = workshop.client.get(f"{ADMIN_LOG_URL}/chains", headers=admin)
    assert log.status_code == 200, log.text
    events: list[str | None] = [item["security_event"] for item in log.json()["items"]]
    assert "login_failed" in events
    assert "logout" in events
    positions = [item["chain_position"] for item in log.json()["items"]]
    assert positions == sorted(positions, reverse=True)
    (failure,) = failed.json()["items"]
    assert failure["action"] == "login"
    assert failure["entity"] == "login_destination"
    assert str(failure["entity_id"]).startswith("dest_")
    assert "995" not in str(failure["entity_id"])
    assert chains.status_code == 200, chains.text
    assert chains.json()["platform"]["status"] == "intact"
    assert chains.json()["broken_chains"] == 0
    assert chains.json()["intact_chains"] >= 2


def test_only_admins_read_the_platform_log_and_only_owners_their_chain(
    workshop: Workshop,
) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    stranger_token, _ = workshop.sign_in_with_phone(STRANGER_PHONE)

    admin_view = workshop.client.get(ADMIN_LOG_URL, headers=bearer(token))
    chains_view = workshop.client.get(f"{ADMIN_LOG_URL}/chains", headers=bearer(token))
    foreign_chain = workshop.client.get(
        f"/v1/businesses/{business_id}/audit-log/chain",
        headers=bearer(stranger_token),
    )
    bad_filter = workshop.client.get(
        ADMIN_LOG_URL,
        params={"security_event": "nonsense"},
        headers=bearer(workshop.sign_in_with_email(ADMIN_EMAIL)[0]),
    )

    assert admin_view.status_code == 403
    assert chains_view.status_code == 403
    assert foreign_chain.status_code == 404
    assert bad_filter.status_code == 422
