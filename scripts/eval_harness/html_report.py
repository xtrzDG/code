"""
A self-contained HTML page of a run: headline numbers, the baseline
comparison, criteria, the niche x language matrix, what each scenario
language's replies read as, and every scenario with
its transcript, failed checks and judge notes. Light and dark follow the
reader's system setting; no script, no external file.
"""

from html import escape
from pathlib import Path

from scripts.eval_harness.eval_report import EvalReport
from scripts.eval_harness.html_languages import render_language_confusion
from scripts.eval_harness.html_sections import (
    render_baseline,
    render_criteria,
    render_judge,
    render_matrix,
    render_scenarios,
    render_tiles,
)

STYLE_PATH: Path = Path(__file__).with_name("report.css")


def render_html(report: EvalReport) -> str:
    models: str = "; ".join(
        f"{used.niche}: {used.assistant}"
        + (f", judge {used.judge}" if used.judge else "")
        for used in report.models
    )
    parts: list[str] = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Assistant evaluation</title>",
        f"<style>{STYLE_PATH.read_text(encoding='utf-8')}</style>",
        "</head><body><main>",
        "<h1>Assistant evaluation</h1>",
        f'<p class="meta">{escape(report.generated_at)} &middot; '
        f"{escape(report.mode)} &middot; {report.samples} sample(s) per scenario"
        f"<br>{escape(models)}</p>",
        render_tiles(report.summary),
        render_baseline(report.baseline),
        render_criteria(report.summary),
        render_judge(report.summary),
        render_matrix(report.summary),
        render_language_confusion(report.summary),
        render_scenarios(report.scenarios),
        "</main></body></html>",
    ]
    return "\n".join(part for part in parts if part) + "\n"
