"""
Reading evaluation datasets and turning their expectations into the typed
DTOs the scorers take.
"""

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import cast

import yaml
from pydantic import ValidationError

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.billing import Money
from app.schemas.dto.evaluations import (
    EvalExpectations,
    ExpectedToolCall,
    RememberedFactGroup,
    RequiredFactGroup,
)
from app.schemas.typings.evaluations.booleans import IsHandoffExpected, IsLeakChecked
from app.schemas.typings.evaluations.constrained_strings import ToolInputFieldName
from app.schemas.typings.evaluations.strings import (
    ExpectedToolFieldValue,
    ForbiddenReplyValue,
    PrivateSeedValue,
    RememberedReplyFact,
    RequiredReplyFact,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.money.money_math import build_money_from_major_units
from scripts.eval_harness.dataset_models import EvalDataset, ScenarioSpec
from scripts.eval_harness.dataset_setup_models import SetupSpec
from scripts.eval_harness.dataset_validation import (
    ScenarioError,
    check_scenario,
    media_directory,
)

DATASET_SUFFIX: str = ".yaml"


class DatasetError(Exception):
    """A dataset file cannot be used (technical error of the harness)."""


def list_dataset_paths(directory: Path, niches: Sequence[str] = ()) -> list[Path]:
    """The dataset files of the asked niches (all when none), by niche."""

    paths: list[Path] = sorted(directory.glob(f"*{DATASET_SUFFIX}"))
    if not niches:
        return paths

    wanted: set[str] = set(niches)
    selected: list[Path] = [path for path in paths if path.stem in wanted]
    missing: set[str] = wanted - {path.stem for path in selected}
    if missing:
        raise DatasetError(f"No dataset for: {', '.join(sorted(missing))}.")

    return selected


def load_dataset(path: Path) -> EvalDataset:
    """
    One dataset, validated: a file named after its niche, unique scenario
    ids, and every scenario playable as written (`check_scenario`: its
    language, goal, channel, media and memory facts).
    """

    try:
        raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
        dataset: EvalDataset = EvalDataset.model_validate(raw)
    except (yaml.YAMLError, ValidationError) as error:
        raise DatasetError(f"{path}: {error}") from error

    if dataset.niche.value != path.stem:
        raise DatasetError(f"{path}: the file of niche {dataset.niche.value}")

    seen: set[str] = set()
    for scenario in dataset.scenarios:
        if scenario.id in seen:
            raise DatasetError(f"{path}: scenario {scenario.id} appears twice.")

        seen.add(scenario.id)
        try:
            check_scenario(scenario, dataset.business.languages, media_directory(path))
        except ScenarioError as error:
            raise DatasetError(f"{path}: {error}") from error

    return dataset


def build_expectations(
    scenario: ScenarioSpec, currency_code: CurrencyCode
) -> EvalExpectations:
    """The scenario's `expect` block as the scorers' typed expectations."""

    expect = scenario.expect
    tool_calls: list[ExpectedToolCall] = []
    for entry in expect.tools:
        if isinstance(entry, AssistantToolName):
            tool_calls.append(ExpectedToolCall(tool_name=entry))
            continue

        for tool_name, fields in entry.items():
            tool_calls.append(
                ExpectedToolCall(
                    tool_name=tool_name,
                    fields={
                        ToolInputFieldName(name): [
                            ExpectedToolFieldValue(field_text(value))
                            for value in acceptable_values(values)
                        ]
                        for name, values in fields.items()
                    },
                )
            )

    return EvalExpectations(
        tool_calls=tool_calls,
        forbidden_tools=list(expect.forbidden_tools),
        prices=[price_money(amount, currency_code) for amount in expect.prices],
        required_facts=[
            RequiredFactGroup(
                values=[
                    RequiredReplyFact(value)
                    for value in (fact if isinstance(fact, list) else [fact])
                ]
            )
            for fact in expect.facts
        ],
        forbidden_values=[ForbiddenReplyValue(value) for value in expect.forbidden],
        is_handoff_expected=(
            None if expect.handoff is None else IsHandoffExpected(expect.handoff)
        ),
        remembered_facts=[
            RememberedFactGroup(
                values=[
                    RememberedReplyFact(value)
                    for value in (fact if isinstance(fact, list) else [fact])
                ]
            )
            for fact in expect.memory
        ],
        is_leak_checked=IsLeakChecked(expect.no_leak),
        private_values=[
            PrivateSeedValue(value) for value in private_texts(scenario.setup)
        ],
    )


def private_texts(setup: SetupSpec | None) -> list[str]:
    """What the scenario seeded that no reply may give away."""

    if setup is None:
        return []

    texts: list[str] = []
    if setup.earlier is not None and setup.earlier.note is not None:
        texts.append(setup.earlier.note)

    if setup.other_customer is not None:
        texts.extend([setup.other_customer.name, setup.other_customer.phone])

    return texts


def acceptable_values(values: object) -> list[object]:
    """A field's acceptable values: a list as it is, one value as a list."""

    return list(cast(list[object], values)) if isinstance(values, list) else [values]


def field_text(value: object) -> str:
    """A field value as the dataset means it: null, true, 2, "Nino"."""

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


def price_money(amount: str, currency_code: CurrencyCode) -> Money:
    """ "25" or "25.50" in the business currency."""

    return build_money_from_major_units(Decimal(amount), currency_code)
