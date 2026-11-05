"""The arithmetic of production quality: sampling, costs, averages and drops."""

from typed_time_provider import Microseconds

from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.quality import QualityTotals
from app.schemas.typings.assistants.constrained_integers import (
    LlmMaxOutputTokens,
    LlmPricePerMillionTokensMicroUsd,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.quality.constrained_integers import (
    QualitySampleBudgetCents,
    QualitySampleCount,
    QualitySamplePercent,
    QualityScoreHundredthsTotal,
)
from app.utilities.quality.quality_costs import cost_of, price_of, worst_case_cost
from app.utilities.quality.quality_prompts import blank_contacts
from app.utilities.quality.quality_sampling import (
    budget_micro_usd,
    is_sampled,
    take_turns,
    to_hundredths,
    utc_day_start,
)
from app.utilities.quality.quality_trend import (
    average_of,
    describe_average,
    drop_percent,
)
from tests.assembly.judge_helpers import scores

CHEAP: LlmTokenPrice = LlmTokenPrice(
    model_id=LlmModelId("gpt-5-mini"),
    input_price=LlmPricePerMillionTokensMicroUsd(250_000),
    output_price=LlmPricePerMillionTokensMicroUsd(2_000_000),
)
DEAR: LlmTokenPrice = LlmTokenPrice(
    model_id=LlmModelId("claude-sonnet-5-5"),
    input_price=LlmPricePerMillionTokensMicroUsd(3_000_000),
    output_price=LlmPricePerMillionTokensMicroUsd(15_000_000),
)


def totals(count: int, hundredths: int) -> QualityTotals:
    return QualityTotals(
        sample_count=QualitySampleCount(count),
        score_hundredths_total=QualityScoreHundredthsTotal(hundredths),
    )


def test_the_sample_is_about_the_percent_and_none_or_all_at_the_edges() -> None:
    ids = [ConversationId() for _ in range(2_000)]

    picked = [item for item in ids if is_sampled(item, QualitySamplePercent(5))]

    assert 50 <= len(picked) <= 150
    assert not any(is_sampled(item, QualitySamplePercent(0)) for item in ids)
    assert all(is_sampled(item, QualitySamplePercent(100)) for item in ids)


def test_businesses_take_turns_and_days_and_budgets_are_whole() -> None:
    assert take_turns([[1, 2, 3], [], [10], [20, 21]]) == [1, 10, 20, 2, 21, 3]
    assert take_turns([]) == []
    assert budget_micro_usd(QualitySampleBudgetCents(500)) == 5_000_000
    day = 86_400_000_000
    assert utc_day_start(Microseconds(3 * day + 5)) == Microseconds(3 * day)


def test_the_average_rounds_half_up_to_hundredths() -> None:
    assert int(to_hundredths(scores())) == 500
    assert int(to_hundredths(scores(handoff=4))) == 480
    assert int(to_hundredths(scores(handoff=4, language=4, booking_data=3))) == 420
    # Three criteria of 5, 5 and 4 average 4.666...: 467 hundredths.
    assert int(to_hundredths(scores(handoff=4)[2:])) == 467


def test_costs_round_up_and_an_unknown_judge_is_priced_as_the_dearest() -> None:
    assert price_of((CHEAP, DEAR), LlmModelId("gpt-5-mini")) == CHEAP
    assert price_of((CHEAP, DEAR), LlmModelId("some-new-model")) == DEAR
    assert int(cost_of(CHEAP, LlmTokenCount(1), LlmTokenCount(0))) == 1
    assert int(cost_of(DEAR, LlmTokenCount(1_000), LlmTokenCount(1_000))) == 18_000
    assert int(worst_case_cost(CHEAP, "x" * 2_999, LlmMaxOutputTokens(1_000))) == (
        2_000 + 250
    )


def test_averages_and_drops_of_stretches() -> None:
    assert average_of(totals(0, 0)) is None
    assert describe_average(totals(0, 0)) == "-"
    assert describe_average(totals(4, 1_840)) == "4.6"
    assert int(drop_percent(totals(10, 4_200), totals(10, 4_800))) == 12
    assert int(drop_percent(totals(10, 4_900), totals(10, 4_800))) == 0
    assert int(drop_percent(totals(0, 0), totals(10, 4_800))) == 0


def test_contacts_are_blanked_whatever_their_case() -> None:
    text = "Write Nino@Example.com or nino@example.com, or call 555 12 34 56."

    blanked = blank_contacts(text, CountryCode("GE"))

    assert blanked == "Write [e-mail] or [e-mail], or call [phone]."
