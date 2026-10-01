from dataclasses import dataclass

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    AutotestOutcome,
    AutotestScenarioKind,
)
from app.schemas.constants.billing import (
    PlanKey,
    SubscriptionStatus,
    UsageKind,
)
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.client_health import (
    CabinetSection,
    ClientHealthIssue,
    ClientHealthStatus,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
    AutotestScenarioResult,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import MessageDocument, ToolCallRecord
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import (
    AdminClientQuery,
    AdminClientsQuery,
    OpenClientCabinetCommand,
)
from app.schemas.dto.billing_cabinet import (
    StartCheckoutCommand,
    StartCheckoutRequest,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.schemas.typings.assistants.constrained_floats import (
    AutotestPassRate,
    AverageJudgeScore,
)
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
)
from app.schemas.typings.assistants.constrained_strings import (
    AutotestScenarioKey,
    LlmModelId,
)
from app.schemas.typings.assistants.strings import JudgeNote, SystemPromptText
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.handoffs.strings import (
    HandoffSummary,
    UnansweredQuestionText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.billing.billing_testbed import (
    GEORGIA,
    ITALY,
    MICROSECONDS_PER_DAY,
    USA,
    BillingTestbed,
)
from tests.billing.test_trial_and_plan import start_trial


@dataclass(frozen=True)
class AdminWorld:
    testbed: BillingTestbed
    admin: UserDocument
    owner: UserDocument
    georgian: BusinessDocument
    italian: BusinessDocument
    american: BusinessDocument


def days_ago(testbed: BillingTestbed, days: float) -> Microseconds:
    return Microseconds(int(testbed.clock.now()) - int(days * MICROSECONDS_PER_DAY))


def add_version(
    testbed: BillingTestbed,
    business: BusinessDocument,
    number: int,
    score: float | None,
    results: list[tuple[str, AutotestOutcome]],
) -> AssistantVersionDocument:
    version = AssistantVersionDocument(
        business_id=business.id,
        version_number=AssistantVersionNumber(number),
        status=AssistantVersionStatus.READY,
        niche_key=NicheKey.ENTERTAINMENT,
        model_id=LlmModelId("gpt-5-mini"),
        prompt_text=SystemPromptText("You are the AI assistant."),
        tools=[AssistantToolName.CREATE_BOOKING],
        languages=[LanguageTag("ka")],
        default_language=LanguageTag("ka"),
        is_voice_enabled=True,
        facts=[],
        profile_revision=testbed.clock.now(),
        test_score=None if score is None else AverageJudgeScore(score),
    )
    if results:
        run = AutotestRunDocument(
            business_id=business.id,
            assistant_version_id=version.id,
            results=[
                AutotestScenarioResult(
                    scenario_key=AutotestScenarioKey(key),
                    kind=AutotestScenarioKind.PRICE_QUESTION,
                    language=LanguageTag("ka"),
                    outcome=outcome,
                    judge_notes=(
                        [JudgeNote("Price invented")]
                        if outcome is AutotestOutcome.FAILED
                        else []
                    ),
                )
                for key, outcome in results
            ],
            pass_rate=AutotestPassRate(0.5),
            is_passed=False,
        )
        testbed.autotest_run_repo.save(run)
        version.autotest_run_id = run.id

    testbed.assistant_version_repo.save(version)
    return version


def add_handoff(
    testbed: BillingTestbed,
    business: BusinessDocument,
    created_at: Microseconds,
    is_sandbox: bool = False,
) -> None:
    testbed.handoff_repo.save(
        HandoffDocument(
            business_id=business.id,
            conversation_id=ConversationId(),
            contact_id=ContactId(),
            reason=HandoffReason.COMPLAINT,
            summary=HandoffSummary("Guest is unhappy"),
            is_sandbox=is_sandbox,
            created_at=created_at,
            updated_at=created_at,
        )
    )


def add_question(
    testbed: BillingTestbed,
    business: BusinessDocument,
    is_resolved: bool = False,
    is_sandbox: bool = False,
) -> None:
    testbed.question_repo.save(
        UnansweredQuestionDocument(
            business_id=business.id,
            question=UnansweredQuestionText("Is there parking?"),
            language=LanguageTag("ka"),
            last_seen_at=testbed.clock.now(),
            is_resolved=is_resolved,
            is_sandbox=is_sandbox,
        )
    )


def add_tool_message(
    testbed: BillingTestbed,
    business: BusinessDocument,
    created_at: Microseconds,
    errors: int,
) -> None:
    testbed.message_repo.save(
        MessageDocument(
            conversation_id=ConversationId(),
            business_id=business.id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.ASSISTANT,
            text=MessageText("Let me check."),
            tool_calls=[
                ToolCallRecord(
                    tool_name=AssistantToolName.CHECK_AVAILABILITY,
                    input_json=LlmToolInputJson("{}"),
                    result_json=LlmToolResultJson('{"error": "timeout"}'),
                    is_error=index < errors,
                )
                for index in range(errors + 1)
            ],
            created_at=created_at,
            updated_at=created_at,
        )
    )


def build_admin_world() -> AdminWorld:
    testbed = BillingTestbed()
    admin = testbed.add_user(email="dani@example.com", is_platform_admin=True)
    owner = testbed.add_user(email="owner@example.com")
    georgian = testbed.add_business(owner, GEORGIA, name="Funicular VR")
    italian = testbed.add_business(owner, ITALY, name="Bella Napoli")
    american = testbed.add_business(
        testbed.add_user(email="us@example.com"),
        USA,
        plan_key=PlanKey.CHAT,
        name="Austin Bikes",
    )
    start_trial(testbed, owner, georgian)
    start_trial(testbed, owner, italian)

    published = add_version(
        testbed, georgian, 1, 4.6, [("price__ka", AutotestOutcome.PASSED)]
    )
    add_version(
        testbed,
        georgian,
        2,
        3.8,
        [
            ("price__ka", AutotestOutcome.PASSED),
            ("booking__ru", AutotestOutcome.FAILED),
            ("handoff__en", AutotestOutcome.ERRORED),
        ],
    )
    published.published_at = days_ago(testbed, 3)
    testbed.assistant_version_repo.save(published)
    stored_georgian = testbed.business(georgian.id)
    stored_georgian.published_assistant_version_id = published.id
    testbed.business_repo.save(stored_georgian)
    add_handoff(testbed, georgian, days_ago(testbed, 1))
    add_handoff(testbed, georgian, days_ago(testbed, 6))
    add_handoff(testbed, georgian, days_ago(testbed, 2), is_sandbox=True)
    add_handoff(testbed, georgian, days_ago(testbed, 9))
    add_question(testbed, georgian)
    add_question(testbed, georgian, is_resolved=True)
    add_question(testbed, georgian, is_sandbox=True)
    add_tool_message(testbed, georgian, days_ago(testbed, 1), errors=2)
    add_tool_message(testbed, georgian, days_ago(testbed, 10), errors=1)
    testbed.record_usage(georgian.id, UsageKind.VOICE_SECONDS, 12_000)
    testbed.record_usage(georgian.id, UsageKind.DIALOG, 25)

    subscription = testbed.subscription(italian.id)
    subscription.status = SubscriptionStatus.PAST_DUE
    testbed.subscription_repo.save(subscription)
    stored_italian = testbed.business(italian.id)
    stored_italian.service_mode = ServiceMode.LEADS_ONLY
    testbed.business_repo.save(stored_italian)
    return AdminWorld(
        testbed=testbed,
        admin=admin,
        owner=owner,
        georgian=georgian,
        italian=italian,
        american=american,
    )


def test_admin_pages_are_for_platform_admins_only() -> None:
    world = build_admin_world()

    with pytest.raises(AccessDeniedError):
        world.testbed.list_clients.run(AdminClientsQuery(user_id=world.owner.id))

    with pytest.raises(AccessDeniedError):
        world.testbed.get_client_health.run(
            AdminClientQuery(user_id=world.owner.id, business_id=world.georgian.id)
        )

    with pytest.raises(AccessDeniedError):
        world.testbed.open_client_cabinet.run(
            OpenClientCabinetCommand(
                user_id=world.owner.id,
                business_id=world.georgian.id,
            )
        )

    assert world.testbed.audit_log_repo.list_by_business(world.georgian.id) == []


def test_client_list_shows_health_with_critical_clients_first() -> None:
    world = build_admin_world()

    listing = world.testbed.list_clients.run(AdminClientsQuery(user_id=world.admin.id))

    assert int(listing.client_count) == 3
    assert listing.generated_at == world.testbed.clock.now()
    assert [str(client.name) for client in listing.clients] == [
        "Bella Napoli",
        "Austin Bikes",
        "Funicular VR",
    ]
    italian, american, georgian = listing.clients
    assert italian.health_status is ClientHealthStatus.CRITICAL
    assert italian.health_issues == [
        ClientHealthIssue.LEADS_ONLY_MODE,
        ClientHealthIssue.PAYMENT_PAST_DUE,
        ClientHealthIssue.NOT_PUBLISHED,
    ]
    assert american.health_status is ClientHealthStatus.ATTENTION
    assert american.health_issues == [ClientHealthIssue.NO_SUBSCRIPTION]
    assert american.subscription_status is None
    assert american.plan_key is PlanKey.CHAT
    assert georgian.health_status is ClientHealthStatus.ATTENTION
    assert georgian.health_issues == [
        ClientHealthIssue.AUTOTESTS_FAILED,
        ClientHealthIssue.TOOL_ERRORS,
    ]
    assert georgian.subscription_status is SubscriptionStatus.TRIALING
    assert int(georgian.published_version_number or 0) == 1
    assert georgian.last_test_score == pytest.approx(3.8)
    assert int(georgian.failed_tests) == 2
    assert int(georgian.handoffs_last_7_days) == 2
    assert int(georgian.open_unanswered_questions) == 1
    assert int(georgian.tool_errors_last_7_days) == 2
    assert int(georgian.used_voice_minutes) == 200
    assert int(georgian.included_voice_minutes) == 400
    assert int(georgian.used_dialogs) == 25
    assert georgian.cost.revenue.currency_code == "GEL"
    assert georgian.cost.margin is None


def test_client_health_explains_the_summary() -> None:
    world = build_admin_world()
    world.testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=world.owner.id,
            business_id=world.georgian.id,
            request=StartCheckoutRequest(),
        )
    )

    health = world.testbed.get_client_health.run(
        AdminClientQuery(user_id=world.admin.id, business_id=world.georgian.id)
    )

    assert health.summary.business_id == world.georgian.id
    assert str(health.timezone) == "Asia/Tbilisi"
    assert [
        (str(test.scenario_key), test.outcome, [str(note) for note in test.judge_notes])
        for test in health.failed_autotests
    ] == [
        ("booking__ru", AutotestOutcome.FAILED, ["Price invented"]),
        ("handoff__en", AutotestOutcome.ERRORED, []),
    ]
    assert len(health.invoices) == 2
    [payment] = health.payments
    assert int(payment.amount.amount_minor) == 96000
    assert world.testbed.audit_log_repo.list_by_business(world.georgian.id) == []


def test_client_health_of_an_unknown_business_is_not_found() -> None:
    world = build_admin_world()

    with pytest.raises(NotFoundError):
        world.testbed.get_client_health.run(
            AdminClientQuery(user_id=world.admin.id, business_id=BusinessId())
        )

    with pytest.raises(NotFoundError):
        world.testbed.open_client_cabinet.run(
            OpenClientCabinetCommand(user_id=world.admin.id, business_id=BusinessId())
        )


def test_entering_a_client_cabinet_is_audited() -> None:
    world = build_admin_world()

    access = world.testbed.open_client_cabinet.run(
        OpenClientCabinetCommand(
            user_id=world.admin.id,
            business_id=world.italian.id,
            client_ip_address=ClientIpAddress("203.0.113.7"),
        )
    )

    [entry] = world.testbed.audit_log_repo.list_by_business(world.italian.id)
    assert entry.action is AuditAction.ADMIN_ACCESS
    assert entry.actor_id == world.admin.id
    assert str(entry.ip_address) == "203.0.113.7"
    assert str(entry.entity) == "business_cabinet"
    assert access.audit_log_entry_id == entry.id
    assert access.sections == list(CabinetSection)
    assert str(access.owner_language) == "it"
    assert access.opened_at == world.testbed.clock.now()


def test_admin_access_follows_the_platform_admin_flag() -> None:
    world = build_admin_world()
    query = AdminClientsQuery(user_id=world.admin.id)
    world.testbed.list_clients.run(query)
    demoted = world.admin.model_copy(update={"is_platform_admin": False})
    world.testbed.user_repo.save(demoted)

    with pytest.raises(AccessDeniedError):
        world.testbed.list_clients.run(query)
