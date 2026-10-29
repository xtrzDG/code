"""
QUALITY_DROP: the judge's scores of the last day's sample against the 7
days before, firing above a 10% drop once both hold 10 scored conversations.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.dto.platform_alerts import AlertObservation
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.quality.constrained_integers import (
    ConversationQualityHundredths,
)
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.utilities.quality.quality_sampling import quality_score_id_of
from tests.assembly.judge_helpers import scores
from tests.platform_ops.ops_documents import HOUR, NOW, at
from tests.platform_ops.ops_world import OpsWorld, put

SHOP: BusinessId = BusinessId()


def scored(
    hundredths: int, judged_at: Microseconds
) -> ConversationQualityScoreDocument:
    conversation_id = ConversationId()
    return ConversationQualityScoreDocument(
        id=quality_score_id_of(conversation_id),
        business_id=SHOP,
        conversation_id=conversation_id,
        assistant_version_id=AssistantVersionId(),
        channel=ChannelKind.TELEGRAM,
        scores=scores(),
        score_hundredths=ConversationQualityHundredths(hundredths),
        judge_model_id=LlmModelId("claude-sonnet-5-5"),
        cost_micro_usd=CostMicroUsd(900),
        judged_at=judged_at,
        created_at=judged_at,
        updated_at=judged_at,
    )


def observe(world: OpsWorld) -> AlertObservation:
    code = PlatformAlertCode.QUALITY_DROP
    [observation] = world.checks().run({code: PLATFORM_ALERT_RULES[code]}, NOW)
    return observation


def night(world: OpsWorld, hundredths: int, hours_ago: int, count: int) -> None:
    put(
        world.quality_scores,
        *(scored(hundredths, at(-hours_ago * HOUR)) for _ in range(count)),
    )


def test_a_drop_of_more_than_ten_percent_fires() -> None:
    world = OpsWorld()
    night(world, 480, hours_ago=50, count=10)
    night(world, 420, hours_ago=2, count=10)

    observation = observe(world)

    assert observation.is_firing
    assert int(observation.figure) == 12
    assert "10 real conversations scored in the last day averaged 4.2" in str(
        observation.detail
    )


def test_a_small_drop_or_a_thin_sample_does_not_fire() -> None:
    world = OpsWorld()
    quiet = observe(world)
    night(world, 480, hours_ago=50, count=10)
    night(world, 450, hours_ago=2, count=10)
    small = observe(world)
    thin = OpsWorld()
    night(thin, 480, hours_ago=50, count=10)
    night(thin, 300, hours_ago=2, count=9)

    assert not quiet.is_firing and int(quiet.figure) == 0
    assert not small.is_firing and int(small.figure) == 6
    assert not observe(thin).is_firing
