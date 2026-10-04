"""Writing a run's report.json and report.html."""

from pathlib import Path

from scripts.eval_harness.eval_report import EvalReport
from scripts.eval_harness.html_report import render_html

REPORT_JSON: str = "report.json"
REPORT_HTML: str = "report.html"


def write_reports(directory: Path, report: EvalReport) -> list[Path]:
    """Write both files into `directory`; returns their paths."""

    directory.mkdir(parents=True, exist_ok=True)
    json_path: Path = directory / REPORT_JSON
    html_path: Path = directory / REPORT_HTML
    json_path.write_text(report.model_dump_json(indent=1) + "\n", encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")
    return [json_path, html_path]
