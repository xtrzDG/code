"use client";

import { IconAlert, IconCheckCircle, IconChevronDown, IconXCircle } from "@/components/icons";
import { Badge, type BadgeTone } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  criterionScore,
  formatScore,
  JUDGE_CRITERIA,
  scenarioAverage,
  scenarioNumber,
  scoreTone,
  type AutotestOutcome,
  type AutotestScenarioResult,
  type JudgeCriterion,
} from "@/lib/assistant/autotests";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";

import { SCENARIO_KIND_LABELS } from "../_lib/scenarioLabels";

const CRITERION_LABELS: Record<JudgeCriterion, MessageKey> = {
  facts_and_prices: "assistant.autotests.criteria.facts_and_prices",
  booking_data: "assistant.autotests.criteria.booking_data",
  ai_disclosure: "assistant.autotests.criteria.ai_disclosure",
  handoff: "assistant.autotests.criteria.handoff",
  language: "assistant.autotests.criteria.language",
};

const OUTCOMES: Record<AutotestOutcome, { tone: BadgeTone; label: MessageKey; icon: typeof IconCheckCircle }> = {
  passed: { tone: "success", label: "assistant.autotests.outcomes.passed", icon: IconCheckCircle },
  failed: { tone: "danger", label: "assistant.autotests.outcomes.failed", icon: IconXCircle },
  errored: { tone: "warning", label: "assistant.autotests.outcomes.errored", icon: IconAlert },
};


/** One scenario of a run, folded: outcome and score; open, the judge's scores, notes and the transcript. */
export function ScenarioResult({ result }: { result: AutotestScenarioResult }) {
  const { t, locale } = useI18n();
  const outcome = OUTCOMES[result.outcome];
  const average = scenarioAverage(result);
  const number = scenarioNumber(result.scenario_key);
  const Icon = outcome.icon;
  const notes = [...result.check_notes, ...result.judge_notes];

  return (
    <li>
      <details className="group rounded-xl border border-line bg-surface open:shadow-sm">
        <summary className="flex cursor-pointer list-none items-center gap-3 rounded-xl px-4 py-3 hover:bg-surface-muted/60 focus-visible:outline-2 focus-visible:outline-focus [&::-webkit-details-marker]:hidden">
          <Icon className={cn("size-5 shrink-0", result.outcome === "passed" ? "text-success" : result.outcome === "failed" ? "text-danger" : "text-warning")} aria-hidden />
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-medium text-ink">
              {number !== null
                ? t("assistant.autotests.numbered", { name: t(SCENARIO_KIND_LABELS[result.kind]), number })
                : t(SCENARIO_KIND_LABELS[result.kind])}
            </span>
            <span className="block text-sm text-ink-subtle">
              {languageName(result.language, locale)}
              {average !== null ? ` · ${t("assistant.autotests.scoreValue", { score: formatScore(average, locale) })}` : ""}
            </span>
          </span>
          <Badge tone={outcome.tone}>{t(outcome.label)}</Badge>
          <IconChevronDown className="size-4 shrink-0 text-ink-subtle transition-transform group-open:rotate-180" aria-hidden />
        </summary>
        <div className="space-y-4 border-t border-line px-4 py-4">
          {result.scores.length > 0 ? (
            <div>
              <h4 className="mb-2 text-xs font-semibold tracking-wide text-ink-muted uppercase">{t("assistant.autotests.scores")}</h4>
              <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
                {JUDGE_CRITERIA.map((criterion) => {
                  const score = criterionScore(result, criterion);
                  return (
                    <li key={criterion} className="flex items-center justify-between gap-2 rounded-lg bg-surface-muted px-3 py-2 text-sm lg:flex-col lg:items-start">
                      <span className="text-ink-muted">{t(CRITERION_LABELS[criterion])}</span>
                      {score !== null ? (
                        <Badge tone={scoreTone(score)}>{t("assistant.autotests.criterionScore", { score })}</Badge>
                      ) : (
                        <span className="text-ink-subtle">—</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
          {notes.length > 0 ? (
            <div>
              <h4 className="mb-2 text-xs font-semibold tracking-wide text-ink-muted uppercase">{t("assistant.autotests.notes")}</h4>
              <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
                {notes.map((note, index) => (
                  <li key={index} dir="auto">
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <div>
            <h4 className="mb-2 text-xs font-semibold tracking-wide text-ink-muted uppercase">{t("assistant.autotests.transcript")}</h4>
            {result.transcript.length === 0 ? (
              <p className="text-sm text-ink-subtle">{t("assistant.autotests.noTranscript")}</p>
            ) : (
              <ol className="space-y-2">
                {result.transcript.map((line, index) => (
                  <li
                    key={index}
                    className={cn(
                      "max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap break-words",
                      line.author === "customer" ? "ml-auto bg-accent-soft text-ink" : line.author === "assistant" ? "bg-surface-muted text-ink" : "mx-auto bg-warning-soft text-ink-muted",
                    )}
                  >
                    <span className="mb-0.5 block text-xs font-medium text-ink-subtle">{t(`assistant.authors.${line.author}`)}</span>
                    <span dir="auto">{line.text}</span>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </details>
    </li>
  );
}
