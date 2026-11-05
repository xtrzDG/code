"""The per-language confusion section of the HTML report (see html_report)."""

from html import escape

from scripts.eval_harness.html_sections import percent
from scripts.eval_harness.language_confusion import LanguageConfusionRow
from scripts.eval_harness.run_summary import RunSummary


def render_language_confusion(summary: RunSummary) -> str:
    """What the replies of each scenario language read as; misses first."""

    if not summary.language_confusion:
        return ""

    rows: list[str] = [
        render_row(row)
        for row in sorted(
            summary.language_confusion,
            key=lambda item: (-item.mismatched, item.expected),
        )
    ]
    return (
        "<h2>Reply languages</h2>"
        '<p class="meta">What each written reply reads as, by the scenario\'s '
        "language (? = too short to tell).</p>"
        "<table><thead><tr><th>Scenario language</th><th>Replies</th>"
        "<th>Read as</th><th>Other language</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_row(row: LanguageConfusionRow) -> str:
    read_as: str = ", ".join(
        f"{escape(language)} {count}" for language, count in row.read_as.items()
    )
    share: float = row.mismatched / row.replies if row.replies else 0.0
    css: str = "bad" if row.mismatched else "good"
    return (
        f"<tr><td>{escape(row.expected)}</td><td>{row.replies}</td>"
        f"<td>{read_as}</td>"
        f'<td class="{css}">{row.mismatched} ({percent(share)})</td></tr>'
    )
