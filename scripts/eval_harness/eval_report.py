"""The report of a run: report.json for machines, report.html for people."""

from pydantic import BaseModel, Field

from scripts.eval_harness.baselines import BaselineDiff
from scripts.eval_harness.run_results import ScenarioResult
from scripts.eval_harness.run_summary import RunSummary


class ModelsUsed(BaseModel):
    niche: str
    assistant: str
    customer: str
    judge: str | None = None


class EvalReport(BaseModel):
    generated_at: str
    mode: str
    samples: int
    models: list[ModelsUsed] = Field(default_factory=list[ModelsUsed])
    summary: RunSummary
    baseline: BaselineDiff | None = None
    scenarios: list[ScenarioResult] = Field(default_factory=list[ScenarioResult])
