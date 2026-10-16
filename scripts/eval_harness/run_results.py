"""What an evaluation run found, sample by sample and in total."""

from pydantic import BaseModel, Field

from app.schemas.dto.evaluations import EvalCriterionResult


class TranscriptLine(BaseModel):
    author: str
    text: str


class JudgeResult(BaseModel):
    """The judge model's scores (1-5 per criterion) and its notes."""

    scores: dict[str, int]
    notes: list[str] = Field(default_factory=list[str])


class SampleResult(BaseModel):
    """
    One play of a scenario. It passes when every deterministic criterion
    holds, the judge (when there is one) scored nothing below 3, the
    conversation ran to its end and, on replay, every call was recorded.
    `reply_languages` is the language each written reply read as ("?" when
    it told too little), for the per-language confusion of the report.
    """

    sample_index: int
    is_passed: bool
    criteria: list[EvalCriterionResult] = Field(
        default_factory=list[EvalCriterionResult]
    )
    reply_languages: list[str] = Field(default_factory=list[str])
    judge: JudgeResult | None = None
    transcript: list[TranscriptLine] = Field(default_factory=list[TranscriptLine])
    tool_calls: list[str] = Field(default_factory=list[str])
    cost_micro_usd: int = 0
    turn_latencies_ms: list[int] = Field(default_factory=list[int])
    stale_reasons: list[str] = Field(default_factory=list[str])
    error: str | None = None


class ScenarioResult(BaseModel):
    """Every sample of one scenario; pass^k needs all of them to pass."""

    niche: str
    scenario_id: str
    language: str
    kind: str
    samples: list[SampleResult]

    @property
    def key(self) -> str:
        return f"{self.niche}/{self.scenario_id}"

    @property
    def is_passed(self) -> bool:
        return bool(self.samples) and all(sample.is_passed for sample in self.samples)

    @property
    def is_stale(self) -> bool:
        return any(sample.stale_reasons for sample in self.samples)
