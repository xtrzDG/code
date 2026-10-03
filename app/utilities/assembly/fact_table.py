"""Appending rows to a fact table with unique, valid keys."""

from app.schemas.domain.assistants import BusinessFact
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue

MAX_BASE_KEY_LENGTH: int = 58


def build_unique_fact_key(base_key: str, used_keys: set[str]) -> FactKey:
    """
    `base_key`, or `base_key_2`, `base_key_3`... when it is already used.
    The key is recorded in `used_keys`.
    """

    truncated_key: str = base_key[:MAX_BASE_KEY_LENGTH]
    candidate_key: str = truncated_key
    suffix: int = 2
    while candidate_key in used_keys:
        candidate_key = f"{truncated_key}_{suffix}"
        suffix += 1

    used_keys.add(candidate_key)
    return FactKey(candidate_key)


def append_fact(
    facts: list[BusinessFact],
    used_keys: set[str],
    base_key: str,
    label: str,
    value: str,
) -> None:
    """Add one row; blank labels or values are never added."""

    if label.strip() == "" or value.strip() == "":
        return

    facts.append(
        BusinessFact(
            key=build_unique_fact_key(base_key, used_keys),
            label=FactLabel(label.strip()),
            value=FactValue(value.strip()),
        )
    )
