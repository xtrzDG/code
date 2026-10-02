"""Three clients in different health for the platform admin tests."""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    AutotestOutcome,
    AutotestScenarioKind,
)
from app.schemas.constants.billing import PlanKey, SubscriptionStatus, UsageKind
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.channels import MessageDirection
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
from app.schemas.typings.assistants.constrained_floats import (
    AutotestPassRate,
    AverageJudgeScore,
)
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import (
    AutotestScenarioKey,
    LlmModelId,
)
from app.schemas.typings.assistants.strings import JudgeNote, SystemPromptText
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.handoffs.strings import HandoffSummary, UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.billing.billing_settings import GEORGIA, ITALY, MICROSECONDS_PER_DAY, USA
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.plan_steps import start_trial


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
