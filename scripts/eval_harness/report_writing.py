"""Writing a run's report.json, report.html and summary.md."""

from pathlib import Path

from scripts.eval_harness.eval_report import EvalReport
from scripts.eval_harness.html_report import render_html
from scripts.eval_harness.report_markdown import render_markdown

REPORT_JSON: str = "report.json"
REPORT_HTML: str = "report.html"
REPORT_MARKDOWN: str = "summary.md"


def write_reports(directory: Path, report: EvalReport) -> list[Path]:
    """Write the three files into `directory`; returns their paths."""

    directory.mkdir(parents=True, exist_ok=True)
    json_path: Path = directory / REPORT_JSON
    html_path: Path = directory / REPORT_HTML
    json_path.write_text(report.model_dump_json(indent=1) + "\n", encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")
    markdown_path: Path = directory / REPORT_MARKDOWN
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return [json_path, html_path, markdown_path]
