"""
Checks of a dataset scenario beyond its shape (dataset_loading.load_dataset):
what a typo or a forgotten field would otherwise turn into a scenario that
quietly tests nothing.
"""

from pathlib import Path

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.evaluations import EvalFlowKind
from scripts.eval_harness.dataset_models import ScenarioSpec
from scripts.eval_harness.dataset_setup_models import ScenarioChannel, SetupSpec

# Where the photos a scenario sends live: evals/media next to evals/datasets.
MEDIA_DIRECTORY_NAME: str = "media"


class ScenarioError(Exception):
    """A scenario cannot be played as written (technical error of the harness)."""


def media_directory(dataset_path: Path) -> Path:
    return dataset_path.parent.parent / MEDIA_DIRECTORY_NAME


def check_scenario(
    scenario: ScenarioSpec, languages: list[str], media_dir: Path
) -> None:
    """Raise ScenarioError naming the first rule the scenario breaks."""

    check_language(scenario, languages)
    if isinstance(scenario.kind, EvalFlowKind) and scenario.goal is None:
        raise ScenarioError(
            f"{scenario.id} plays {scenario.kind.value}, which needs a goal."
        )

    is_customer: bool = scenario.channel is not ScenarioChannel.OWNER_TEST
    needs_customer: bool = scenario.setup is not None or scenario.attachment is not None
    if needs_customer and not (is_customer and scenario.persona.phone):
        raise ScenarioError(
            f"{scenario.id} seeds what a customer has or sends media: it is "
            "played on whatsapp by a persona with a phone number."
        )

    check_attachment(scenario, media_dir)
    check_memory(scenario)


def check_language(scenario: ScenarioSpec, languages: list[str]) -> None:
    """
    A foreign-language scenario is in a language the business does not
    list; a transliterated one may be in either (Armenian typed in Latin
    letters to a Georgian business); every other one in a listed one.
    """

    if not languages or scenario.kind is AutotestScenarioKind.TRANSLITERATED:
        return

    is_foreign: bool = scenario.kind is AutotestScenarioKind.FOREIGN_LANGUAGE
    if (scenario.language in languages) is is_foreign:
        raise ScenarioError(
            f"{scenario.id} is in {scenario.language}; the business speaks "
            f"{', '.join(languages)}, and only a foreign-language scenario is "
            "in a language it does not speak."
        )


def check_attachment(scenario: ScenarioSpec, media_dir: Path) -> None:
    attachment = scenario.attachment
    photo: str | None = None if attachment is None else attachment.photo
    if attachment is not None and attachment.voice_note == (photo is not None):
        raise ScenarioError(
            f"{scenario.id}: an attachment is either a voice note or a photo."
        )

    if photo is not None and not (media_dir / photo).is_file():
        raise ScenarioError(f"{scenario.id}: no photo {media_dir / photo}.")

    if photo is None and any(step.sees_photo for step in scenario.assistant):
        raise ScenarioError(f"{scenario.id}: a step sees a photo nobody sent.")


def check_memory(scenario: ScenarioSpec) -> None:
    """Every remembered fact comes from what the scenario seeded."""

    remembered: str = describe_memory(scenario.setup).casefold()
    for fact in scenario.expect.memory:
        spellings: list[str] = fact if isinstance(fact, list) else [fact]
        if not any(spelling.casefold() in remembered for spelling in spellings):
            raise ScenarioError(
                f"{scenario.id}: the memory fact {spellings!r} is not in what "
                "the scenario seeded (setup.earlier, setup.booking)."
            )


def describe_memory(setup: SetupSpec | None) -> str:
    """What the customer memory will hold, as text: summaries, orders, bookings."""

    if setup is None:
        return ""

    parts: list[str] = []
    if setup.earlier is not None:
        parts.append(setup.earlier.summary)
        parts.append(setup.earlier.lead or "")

    if setup.booking is not None:
        parts.append(setup.booking.date)
        parts.append(setup.booking.time or "")

    return "\n".join(parts)
