"""
How a dataset scenario is played: the autotest scenario it stands for (the
evaluation-only flows are played as an autotest kind), the message an
attack or an owner check opens with word for word, and where the persona
writes from (`CustomerSide`).
"""

from pathlib import Path

from app.containers.app import AppContainer
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.evaluations import EvalFlowKind
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.assistants.strings import (
    AutotestOpeningMessage,
    AutotestScenarioGoal,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.assembly.autotest_scenarios import (
    DEFAULT_PARTY_SIZE,
    RED_TEAM_SCENARIO_KINDS,
    plan_scenarios,
)
from app.utilities.assembly.fact_descriptions import RESOURCE_KIND_NOUNS
from app.utilities.assembly.fact_formatting import read_english_text
from app.utilities.assembly.language_profiles import (
    build_autotest_languages,
    collect_language_profiles,
)
from scripts.eval_harness.business_seeding import SeededBusiness
from scripts.eval_harness.conversation_loop import CustomerSide, owner_test_side
from scripts.eval_harness.dataset_models import EvalDataset, ScenarioSpec
from scripts.eval_harness.dataset_setup_models import ScenarioChannel
from scripts.eval_harness.media_inputs import FirstMessageMedia
from scripts.eval_harness.scenario_seeding import customer_channel_user_id

# The autotest kind each evaluation-only flow is played as: its checks of
# what was created fit (none for a booking change or a price question).
EVAL_FLOW_BASE_KINDS: dict[EvalFlowKind, AutotestScenarioKind] = {
    EvalFlowKind.RESCHEDULE: AutotestScenarioKind.CANCELLATION,
    EvalFlowKind.MY_BOOKINGS: AutotestScenarioKind.CANCELLATION,
    EvalFlowKind.RETURNING_CUSTOMER: AutotestScenarioKind.PRICE_QUESTION,
    EvalFlowKind.VOICE_NOTE: AutotestScenarioKind.PRICE_QUESTION,
    EvalFlowKind.PHOTO_MENU: AutotestScenarioKind.PRICE_QUESTION,
}
# Kinds whose first message is sent word for word, as the autotests send it.
OPENING_KINDS: frozenset[AutotestScenarioKind] = frozenset(
    {*RED_TEAM_SCENARIO_KINDS, AutotestScenarioKind.OWNER_CHECK}
)


def autotest_kind(scenario: ScenarioSpec) -> AutotestScenarioKind:
    kind = scenario.kind
    return EVAL_FLOW_BASE_KINDS[kind] if isinstance(kind, EvalFlowKind) else kind


def plan_eval_scenario(
    container: AppContainer, dataset: EvalDataset, scenario: ScenarioSpec
) -> AutotestScenario:
    """
    The autotest scenario the dataset scenario stands for, planned like an
    autotest run plans it (language name and script, the kind's goal or the
    price question of `item`), under the dataset's id and goal, with the
    opening of an attack or an owner check.
    """

    registries = container.registries
    niche = registries.niche_template_registry().get(dataset.niche)
    tag = LanguageTag(scenario.language)
    planned: list[AutotestScenario] = plan_scenarios(
        languages=build_autotest_languages(
            [tag], collect_language_profiles(registries.language_registry(), [tag])
        ),
        kinds=[autotest_kind(scenario)],
        priced_item_titles=[] if scenario.item is None else [scenario.item],
        price_question_limit=1,
        resource_noun=(
            read_english_text(niche.resource_nouns)
            or RESOURCE_KIND_NOUNS[niche.resource_kind]
        ),
        party_size=DEFAULT_PARTY_SIZE,
    )
    base: AutotestScenario = planned[-1]
    return base.model_copy(
        update={
            "key": AutotestScenarioKey(scenario.id),
            "goal": base.goal
            if scenario.goal is None
            else AutotestScenarioGoal(scenario.goal),
            "opening_message": opening_message(scenario),
        }
    )


def opening_message(scenario: ScenarioSpec) -> AutotestOpeningMessage | None:
    if autotest_kind(scenario) not in OPENING_KINDS or not scenario.customer:
        return None

    return AutotestOpeningMessage(scenario.customer[0])


def build_customer_side(
    container: AppContainer,
    seeded: SeededBusiness,
    scenario: ScenarioSpec,
    planned: AutotestScenario,
    media_dir: Path,
) -> CustomerSide:
    """Where the persona writes from and what its first message carries."""

    opening: MessageText | None = (
        None
        if planned.opening_message is None
        else MessageText(str(planned.opening_message))
    )
    phone: str | None = scenario.persona.phone
    if scenario.channel is ScenarioChannel.OWNER_TEST or phone is None:
        side: CustomerSide = owner_test_side(scenario.id)
        return CustomerSide(
            channel=side.channel,
            channel_user_id=side.channel_user_id,
            is_sandbox=side.is_sandbox,
            opening=opening,
        )

    media: FirstMessageMedia | None = (
        None
        if scenario.attachment is None
        else FirstMessageMedia(
            attachment=scenario.attachment,
            storage=container.adapters.media.media_storage(),
            business_id=seeded.business.id,
            media_dir=media_dir,
        )
    )
    return CustomerSide(
        channel=ChannelKind.WHATSAPP,
        channel_user_id=customer_channel_user_id(phone),
        is_sandbox=False,
        phone=E164PhoneNumber(phone),
        name=ContactName(scenario.persona.name),
        opening=opening,
        deliver=None if media is None else media.deliver,
    )
