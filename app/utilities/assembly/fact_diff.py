"""
The difference between two fact tables: what the assistant would learn,
forget or say differently if it were built again now.

Rows numbered in their list (offer items, questions, resources, special
days) are paired by label, the others by key. A special day that has
simply passed is not a change. A changed price of an offer item is
reported with both prices.
"""

from collections import Counter
from collections.abc import Mapping, Sequence

from app.schemas.constants.setup import (
    PendingChangeAction,
    PendingChangeArea,
    PendingChangeDetail,
)
from app.schemas.domain.assistants import BusinessFact
from app.schemas.dto.setup.pending_changes import PendingChange
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.setup.strings import PendingChangeValue
from app.utilities.assembly.fact_changes import (
    describe_fact_change,
    is_matched_by_label,
    read_special_day,
)

# describe_knowledge_item joins the parts of an item with this separator
# and writes its price as "Price: 18.00 GEL".
PART_SEPARATOR: str = "; "
PRICE_PREFIX: str = "Price: "
AREA_ORDER: list[PendingChangeArea] = list(PendingChangeArea)

type FactMatchKey = tuple[str, str, int]


def diff_fact_tables(
    live_facts: Sequence[BusinessFact],
    current_facts: Sequence[BusinessFact],
    today: LocalDate,
    answer_labels: Mapping[str, str],
) -> list[PendingChange]:
    """
    Changes from `live_facts` to `current_facts`, grouped by area in a
    fixed order and in table order within an area.
    """

    live_rows: dict[FactMatchKey, BusinessFact] = index_facts(live_facts)
    current_rows: dict[FactMatchKey, BusinessFact] = index_facts(current_facts)
    changes: list[PendingChange] = []
    for match_key, fact in current_rows.items():
        before: BusinessFact | None = live_rows.get(match_key)
        if before is None:
            changes.append(
                describe_fact_change(fact, PendingChangeAction.ADDED, answer_labels)
            )
        elif before.value != fact.value:
            changes.append(describe_value_change(before, fact, answer_labels))

    for match_key, fact in live_rows.items():
        if match_key in current_rows or has_passed(fact, today):
            continue

        changes.append(
            describe_fact_change(fact, PendingChangeAction.REMOVED, answer_labels)
        )

    return sorted(changes, key=lambda change: AREA_ORDER.index(change.area))


def index_facts(facts: Sequence[BusinessFact]) -> dict[FactMatchKey, BusinessFact]:
    """
    Rows by what pairs them: ("label", label, n) for numbered rows (the
    n-th row with that label) and ("key", key, 0) for the others.
    """

    seen_labels: Counter[str] = Counter()
    rows: dict[FactMatchKey, BusinessFact] = {}
    for fact in facts:
        if is_matched_by_label(str(fact.key)):
            label: str = str(fact.label)
            rows[("label", label, seen_labels[label])] = fact
            seen_labels[label] += 1
        else:
            rows[("key", str(fact.key), 0)] = fact

    return rows


def has_passed(fact: BusinessFact, today: LocalDate) -> bool:
    """A special day before today: it left the table by itself."""

    day: LocalDate | None = read_special_day(fact)
    return day is not None and str(day) < str(today)


def describe_value_change(
    before: BusinessFact,
    after: BusinessFact,
    answer_labels: Mapping[str, str],
) -> PendingChange:
    change: PendingChange = describe_fact_change(
        after, PendingChangeAction.CHANGED, answer_labels
    )
    if change.area is not PendingChangeArea.OFFER:
        return change

    price_before: str | None = read_price(str(before.value))
    price_after: str | None = read_price(str(after.value))
    if price_before == price_after:
        return change.model_copy(update={"detail": PendingChangeDetail.DETAILS})

    return change.model_copy(
        update={
            "detail": PendingChangeDetail.PRICE,
            "before": None
            if price_before is None
            else PendingChangeValue(price_before),
            "after": None if price_after is None else PendingChangeValue(price_after),
        }
    )


def read_price(description: str) -> str | None:
    """
    "18.00 GEL" from an item's description; the price part comes after
    the owner's own text, so the last one is taken.
    """

    prices: list[str] = [
        part.removeprefix(PRICE_PREFIX).strip()
        for part in description.split(PART_SEPARATOR)
        if part.startswith(PRICE_PREFIX)
    ]
    return prices[-1] if prices else None
