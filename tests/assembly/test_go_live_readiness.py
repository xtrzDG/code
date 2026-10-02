from typing import Any

from app.schemas.constants.assistants import AssistantVersionStatus, GoLiveCheckCode
from app.schemas.constants.billing import PlanKey
from app.schemas.dto.assistants.assistant_commands import AssistantVersionQuery
from app.schemas.dto.go_live import GoLiveCheck, GoLiveReadiness
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.international_business_seeds import (
    seed_italian_restaurant,
    seed_online_shop,
)
from tests.assembly.testbed import AssemblyTestbed


def readiness(
    testbed: AssemblyTestbed,
    business_id: BusinessId,
    version_id: AssistantVersionId,
) -> GoLiveReadiness:
    return testbed.get_readiness_use_case.run(
        AssistantVersionQuery(
            user_id=testbed.staff_id,
            business_id=business_id,
            version_id=version_id,
        )
    )


def summarize(checks: list[GoLiveCheck]) -> list[tuple[str, bool, bool, list[str]]]:
    return [
        (
            check.code.value,
            check.is_ok,
            check.is_blocking,
            [str(detail) for detail in check.details],
        )
        for check in checks
    ]


def test_a_ready_version_of_a_launch_ready_business_may_go_live() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    version = testbed.assemble(business.id, run_autotests=True)
    assert version.status is AssistantVersionStatus.READY

    result = readiness(testbed, business.id, version.id)

    assert result.is_ready is True
    assert result.version_number == version.version_number
    assert result.version_status is AssistantVersionStatus.READY
    assert summarize(result.checks) == [
        ("subscription_or_trial", True, True, ["trialing"]),
        ("dpa", True, True, ["2026-10-01"]),
        ("profile_gaps", True, True, []),
        ("staff_contact", True, True, []),
        ("autotests", True, True, ["ready", "finished"]),
    ]
    assert result.autotest_run is not None
    assert result.autotest_run.is_passed is True
    assert result.autotest_run.is_full_coverage is True
    assert result.autotest_run.scenario_count == result.autotest_run.passed_count
    assert result.autotest_run.completed_count == result.autotest_run.scenario_count
    assert result.subscription_status is not None
    assert str(result.dpa_document_version) == "2026-10-01"


def test_every_missing_condition_is_listed_with_its_details() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed, is_launch_ready=False)
    version = testbed.assemble(business.id)
    profile = testbed.profile_repo.get_by_business(business.id)
    assert profile is not None
    profile.hours = []
    testbed.profile_repo.save(profile)

    result = readiness(testbed, business.id, version.id)

    assert result.is_ready is False
    assert result.autotest_run is None
    assert result.subscription_status is None
    assert summarize(result.checks) == [
        ("subscription_or_trial", False, True, ["none"]),
        ("dpa", False, True, ["2026-10-01"]),
        ("profile_gaps", False, True, ["no_opening_hours"]),
        ("staff_contact", False, True, ["no_handoff_contact"]),
        ("autotests", False, True, ["draft"]),
    ]
    assert str(result.checks[2].message) == (
        "Complete the profile (see what to add: no_opening_hours)."
    )


def test_voice_versions_check_the_voice_settings() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = testbed.assemble(business.id, run_autotests=True)

    configured = readiness(testbed, business.id, version.id)
    testbed.voice_provisioner.missing_settings = [
        EnvironmentVariableName("ELEVENLABS_API_KEY")
    ]
    unconfigured = readiness(testbed, business.id, version.id)

    assert summarize(configured.checks)[-1] == (
        "voice_configuration",
        True,
        True,
        [],
    )
    # Development: a warning, the version may still go live (without voice).
    assert summarize(unconfigured.checks)[-1] == (
        "voice_configuration",
        False,
        False,
        ["ELEVENLABS_API_KEY"],
    )
    assert unconfigured.is_ready is True


def test_missing_voice_settings_block_going_live_in_production() -> None:
    testbed = AssemblyTestbed(environment={"APP_ENV": "production"})
    testbed.voice_provisioner.missing_settings = [
        EnvironmentVariableName("ELEVENLABS_WEBHOOK_SECRET")
    ]
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = testbed.assemble(business.id, run_autotests=True)

    result = readiness(testbed, business.id, version.id)

    voice = result.checks[-1]
    assert voice.code is GoLiveCheckCode.VOICE_CONFIGURATION
    assert (voice.is_ok, voice.is_blocking) == (False, True)
    assert result.is_ready is False


def test_chat_versions_have_no_voice_check() -> None:
    testbed = AssemblyTestbed()
    business = seed_online_shop(testbed)
    version = testbed.assemble(business.id, run_autotests=True)

    result = readiness(testbed, business.id, version.id)

    assert GoLiveCheckCode.VOICE_CONFIGURATION not in [
        check.code for check in result.checks
    ]


def test_readiness_and_refusal_reasons_over_http() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed, is_launch_ready=False)
    client = testbed.build_client()
    owner = testbed.bearer(testbed.owner_id)
    base = f"/v1/businesses/{business.id}/assistant-versions"
    version = testbed.assemble(business.id, run_autotests=True)

    response = client.get(
        f"{base}/{version.id}/go-live-readiness",
        headers=testbed.bearer(testbed.staff_id),
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    assert body["is_ready"] is False
    assert [check["code"] for check in body["checks"] if not check["is_ok"]] == [
        "subscription_or_trial",
        "dpa",
        "staff_contact",
    ]

    refused = client.post(f"{base}/{version.id}/publish", headers=owner)
    assert refused.status_code == 409
    assert refused.json()["error"] == "conflict"
    assert refused.json()["message"].startswith("The assistant cannot go live yet:")
    assert [
        (reason["code"], reason["details"]) for reason in refused.json()["reasons"]
    ] == [
        ("subscription_or_trial", ["none"]),
        ("dpa", ["2026-10-01"]),
        ("staff_contact", ["no_handoff_contact"]),
    ]

    stranger = client.get(
        f"{base}/{version.id}/go-live-readiness",
        headers=testbed.bearer(testbed.stranger_id),
    )
    assert stranger.status_code == 404
    assert "reasons" not in stranger.json()
    unknown = client.get(
        f"{base}/{AssistantVersionId()}/go-live-readiness", headers=owner
    )
    assert unknown.status_code == 404
