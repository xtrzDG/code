"""
What a phone world test sets up besides the phone line: a trial with the
card the owner saved (a number may be rented only with one, or once paid)
and a live assistant version that answers calls.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName, AssistantVersionStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_methods import PaymentMethodSummary
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import StartTrialCommand, StartTrialRequest
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText, VoiceAgentId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.shared.billing_records import find_current_subscription
from tests.billing.billing_testbed import BillingTestbed


def start_trial_with_card(
    testbed: BillingTestbed, owner: UserDocument, business: BusinessDocument
) -> None:
    testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id, business_id=business.id, request=StartTrialRequest()
        )
    )
    save_card(testbed, business)


def save_card(testbed: BillingTestbed, business: BusinessDocument) -> None:
    """The card the owner saved, as the payment provider reported it."""

    subscription = find_current_subscription(testbed.subscription_repo, business.id)
    assert subscription is not None
    subscription.payment_method_summary = PaymentMethodSummary(
        provider=PaymentProvider.FLITT, saved_at=Microseconds(testbed.clock.now())
    )
    testbed.subscription_repo.save(subscription)


def live_voice_version(
    business: BusinessDocument, now: int, agent_id: str
) -> AssistantVersionDocument:
    """A published version with calls, its voice agent set up."""

    return AssistantVersionDocument(
        business_id=business.id,
        version_number=AssistantVersionNumber(1),
        status=AssistantVersionStatus.PUBLISHED,
        niche_key=NicheKey.ENTERTAINMENT,
        model_id=LlmModelId("gpt-5-mini"),
        prompt_text=SystemPromptText("You are the AI assistant."),
        tools=[AssistantToolName.CREATE_BOOKING],
        languages=[LanguageTag("ka")],
        default_language=LanguageTag("ka"),
        is_voice_enabled=True,
        facts=[],
        profile_revision=Microseconds(now),
        voice_agent_id=VoiceAgentId(agent_id),
    )
