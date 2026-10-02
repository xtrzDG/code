import pytest

from app.schemas.constants.assistants import (
    AssistantVersionStatus,
    AutotestScenarioKind,
)
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
    AssembleAssistantVersionRequest,
    AssistantVersionQuery,
    AssistantVersionsQuery,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.assembly.builders import (
    build_business,
    seed_georgian_restaurant,
    seed_italian_restaurant,
    seed_online_shop,
)
from tests.assembly.testbed import AssemblyTestbed


def test_first_version_is_a_draft_with_prompt_facts_and_settings() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    profile = testbed.profile_repo.get_by_business(business.id)
    assert profile is not None

    version = testbed.assemble(business.id)

    assert version.version_number == 1
    assert version.status is AssistantVersionStatus.DRAFT
    assert version.model_id == testbed.settings.llm_model_id
    assert version.niche_key is NicheKey.RESTAURANT
    assert version.languages == [
        LanguageTag("ka"),
        LanguageTag("ru"),
        LanguageTag("en"),
    ]
    assert version.default_language == LanguageTag("ka")
    assert version.profile_revision == profile.updated_at
    assert version.test_score is None
    assert version.autotest_run_id is None
    assert version.published_at is None
    assert str(version.prompt_text).startswith("# Role\n")
    assert version.facts[0].value == "Café Rustaveli"
    assert version.created_at == testbed.wall_clock.now_unix()
    stored = testbed.version(business.id, version.id)
    assert stored.prompt_text == version.prompt_text
    assert len(stored.facts) == len(version.facts)


def test_every_assembly_creates_the_next_version() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    other_business = seed_italian_restaurant(testbed)

    numbers = [int(testbed.assemble(business.id).version_number) for _ in range(3)]
    other_number = testbed.assemble(other_business.id).version_number

    assert numbers == [1, 2, 3]
    assert other_number == 1
    assert len(testbed.version_repo.list_by_business(business.id)) == 3


def test_business_moves_from_onboarding_to_testing_only_once() -> None:
    testbed = AssemblyTestbed()
    onboarding = seed_georgian_restaurant(testbed)
    live = seed_italian_restaurant(testbed)
    live.status = BusinessStatus.LIVE
    testbed.business_repo.save(live)

    testbed.assemble(onboarding.id)
    testbed.assemble(live.id)

    assert testbed.business(onboarding.id).status is BusinessStatus.TESTING
    assert testbed.business(live.id).status is BusinessStatus.LIVE


def test_voice_follows_the_plan() -> None:
    testbed = AssemblyTestbed()
    voice_business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    chat_business = seed_online_shop(testbed)
    plus_business = seed_italian_restaurant(testbed)
    plus_business.plan_key = PlanKey.PLUS
    testbed.business_repo.save(plus_business)

    assert testbed.assemble(voice_business.id).is_voice_enabled is True
    assert testbed.assemble(chat_business.id).is_voice_enabled is False
    assert testbed.assemble(plus_business.id).is_voice_enabled is True


def test_assembly_needs_a_profile() -> None:
    testbed = AssemblyTestbed()
    business = build_business(
        testbed,
        name="Empty Bar",
        niche_key=NicheKey.RESTAURANT,
        country_code="GE",
        city=None,
        timezone_name="Asia/Tbilisi",
        currency_code="GEL",
        languages=["ka"],
    )

    with pytest.raises(ValidationFailedError, match="profile"):
        testbed.assemble(business.id)

    assert testbed.version_repo.list_by_business(business.id) == []
    assert testbed.business(business.id).status is BusinessStatus.ONBOARDING


def test_only_the_owner_assembles() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)

    with pytest.raises(AccessDeniedError):
        testbed.assemble(business.id, user_id=testbed.staff_id)

    with pytest.raises(NotFoundError):
        testbed.assemble(business.id, user_id=testbed.stranger_id)

    assert testbed.version_repo.list_by_business(business.id) == []


@pytest.mark.parametrize(
    "request_body",
    [
        AssembleAssistantVersionRequest(languages=[LanguageTag("de")]),
        AssembleAssistantVersionRequest(languages=[]),
        AssembleAssistantVersionRequest(kinds=[AutotestScenarioKind.EMERGENCY]),
        AssembleAssistantVersionRequest(kinds=[]),
    ],
)
def test_invalid_autotest_selection_is_rejected_before_storing(
    request_body: AssembleAssistantVersionRequest,
) -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)

    with pytest.raises(ValidationFailedError):
        testbed.assemble_pipeline.start(
            AssembleAssistantVersionCommand(
                user_id=testbed.owner_id,
                business_id=business.id,
                request=request_body,
            )
        )

    assert testbed.version_repo.list_by_business(business.id) == []


def test_booking_kinds_do_not_apply_to_a_business_without_bookings() -> None:
    testbed = AssemblyTestbed()
    business = seed_online_shop(testbed)

    with pytest.raises(ValidationFailedError, match="booking"):
        testbed.assemble_pipeline.start(
            AssembleAssistantVersionCommand(
                user_id=testbed.owner_id,
                business_id=business.id,
                request=AssembleAssistantVersionRequest(
                    kinds=[AutotestScenarioKind.BOOKING]
                ),
            )
        )


def test_history_lists_newest_first_and_hides_other_businesses() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    other_business = seed_italian_restaurant(testbed)
    first = testbed.assemble(business.id)
    second = testbed.assemble(business.id)
    foreign = testbed.assemble(other_business.id)

    summaries = testbed.list_versions_use_case.run(
        AssistantVersionsQuery(user_id=testbed.staff_id, business_id=business.id)
    )

    assert [summary.id for summary in summaries] == [second.id, first.id]
    with pytest.raises(NotFoundError):
        testbed.get_version_use_case.run(
            AssistantVersionQuery(
                user_id=testbed.owner_id,
                business_id=business.id,
                version_id=foreign.id,
            )
        )

    with pytest.raises(NotFoundError):
        testbed.get_version_use_case.run(
            AssistantVersionQuery(
                user_id=testbed.owner_id,
                business_id=business.id,
                version_id=AssistantVersionId(),
            )
        )


def test_staff_reads_versions_but_strangers_do_not() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    version = testbed.assemble(business.id)

    details = testbed.get_version_use_case.run(
        AssistantVersionQuery(
            user_id=testbed.staff_id,
            business_id=business.id,
            version_id=version.id,
        )
    )

    assert details.prompt_text == version.prompt_text
    with pytest.raises(NotFoundError):
        testbed.list_versions_use_case.run(
            AssistantVersionsQuery(
                user_id=testbed.stranger_id,
                business_id=business.id,
            )
        )


def test_knowledge_edits_change_only_new_versions() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    first = testbed.assemble(business.id)
    for item in testbed.knowledge_repo.list_by_business(business.id):
        if str(item.title) == "Mtsvadi":
            item.is_active = False
            testbed.knowledge_repo.save(item)

    second = testbed.assemble(business.id)

    first_values = [str(fact.value) for fact in first.facts]
    second_values = [str(fact.value) for fact in second.facts]
    assert "Price: 24.00 GEL" in first_values
    assert "Price: 24.00 GEL" not in second_values
    stored_first_values = [
        str(fact.value) for fact in testbed.version(business.id, first.id).facts
    ]
    assert stored_first_values == first_values
