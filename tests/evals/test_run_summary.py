"""Run numbers: pass^k, pass@1, criteria, judge, groups, cost and latency."""

from scripts.eval_harness.run_summary import percentile, summarize
from tests.evals.result_builders import sample, scenario


def test_pass_k_needs_every_sample_and_pass_at_1_counts_samples() -> None:
    summary = summarize(
        [
            scenario("hotel", "en", [sample(True), sample(True)]),
            scenario("hotel", "ka", [sample(True), sample(False)]),
            scenario("clinic", "en", [sample(False, stale=True), sample(False)]),
            scenario("clinic", "ka", [sample(False, error="boom")]),
        ]
    )

    assert (summary.scenario_count, summary.passed_count) == (4, 1)
    assert summary.pass_rate == 0.25
    assert summary.pass_at_1 == round(3 / 7, 4)
    assert (summary.stale_count, summary.errored_count) == (1, 1)
    prices = next(item for item in summary.criteria if item.criterion == "prices")
    assert (prices.checked, prices.passed) == (7, 3)
    assert [(g.niche, g.language, g.passed) for g in summary.groups] == [
        ("clinic", "en", 0),
        ("clinic", "ka", 0),
        ("hotel", "en", 1),
        ("hotel", "ka", 0),
    ]


def test_cost_latency_and_judge_averages() -> None:
    summary = summarize(
        [
            scenario(
                "hotel",
                "en",
                [
                    sample(True, [100, 300], 1_500_000, {"language": 5}),
                    sample(True, [200], 500_000, {"language": 4}),
                ],
            )
        ]
    )

    assert summary.cost_usd == 2.0
    assert (summary.latency_p50_ms, summary.latency_p95_ms) == (200, 300)
    assert summary.judge_averages == {"language": 4.5}


def test_an_empty_run_has_zero_numbers() -> None:
    summary = summarize([])

    assert (summary.pass_rate, summary.pass_at_1, summary.latency_p95_ms) == (0, 0, 0)
    assert percentile([5], 95) == 5
