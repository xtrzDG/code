"use client";

import { useState } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCheckCircle, IconFlask, IconXCircle } from "@/components/content/icons";
import { IconAlert, IconChevronDown } from "@/components/icons";
import { Alert, Badge, Button, EmptyState, Select, Spinner, type BadgeTone } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  criterionScore,
  filterResults,
  formatScore,
  JUDGE_CRITERIA,
  resultLanguages,
  scenarioAverage,
  scenarioNumber,
  scoreTone,
  sortResults,
  summarizeRun,
  type AutotestOutcome,
  type AutotestRunView,
  type AutotestScenarioKind,
  type AutotestScenarioResult,
  type JudgeCriterion,
  type ResultFilter,
} from "@/lib/assistant/autotests";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";

export const SCENARIO_KIND_LABELS: Record<AutotestScenarioKind, MessageKey> = {
  booking: "assistant.autotests.kinds.booking",
  booking_out_of_hours: "assistant.autotests.kinds.booking_out_of_hours",
  cancellation: "assistant.autotests.kinds.cancellation",
  price_question: "assistant.autotests.kinds.price_question",
  unknown_question: "assistant.autotests.kinds.unknown_question",
  discount_request: "assistant.autotests.kinds.discount_request",
  rude_customer: "assistant.autotests.kinds.rude_customer",
  human_request: "assistant.autotests.kinds.human_request",
  prompt_injection: "assistant.autotests.kinds.prompt_injection",
  emergency: "assistant.autotests.kinds.emergency",
};

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

/** The latest autotest run of a version: summary, progress and every scenario with its transcript. */
export function AutotestsPanel({
  run,
  isRunning,
  canRun,
  onRun,
}: {
  run: AutotestRunView | null;
  isRunning: boolean;
  canRun: boolean;
  onRun: () => void;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const [outcome, setOutcome] = useState<ResultFilter>("all");
  const [language, setLanguage] = useState<string>("all");

  if (!run) {
    return (
      <EmptyState
        icon={isRunning ? <Spinner size="md" /> : <IconFlask className="size-6" />}
        title={isRunning ? t("assistant.autotests.startingTitle") : t("assistant.autotests.noRunTitle")}
        description={
          isRunning
            ? t("assistant.autotests.runningHint")
            : canRun
              ? t("assistant.autotests.noRunDescription")
              : t("assistant.autotests.noRunStaff")
        }
        action={
          canRun && !isRunning ? (
            <Button leadingIcon={<IconFlask className="size-4" aria-hidden />} onClick={onRun}>
              {t("assistant.autotests.run")}
            </Button>
          ) : undefined
        }
      />
    );
  }

  const summary = summarizeRun(run);
  const languages = resultLanguages(run.results);
  const visible = sortResults(filterResults(run.results, { outcome, language }));
  const percent = new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 0 });

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label={t("assistant.autotests.passed")} value={t("assistant.autotests.passedValue", { passed: summary.passed, total: summary.total })} />
        <Stat
          label={t("assistant.autotests.averageScore")}
          value={run.average_score !== null && run.average_score !== undefined ? t("assistant.autotests.scoreValue", { score: formatScore(run.average_score, locale) }) : "—"}
          tone={run.average_score !== null && run.average_score !== undefined ? scoreTone(run.average_score) : undefined}
        />
        <Stat
          label={t("assistant.autotests.result")}
          value={
            isRunning
              ? t("assistant.autotests.running")
              : run.status === "errored"
                ? t("assistant.autotests.outcomes.errored")
                : run.is_passed
                  ? t("assistant.autotests.runPassed")
                  : t("assistant.autotests.runFailed")
          }
          tone={isRunning ? "info" : run.status === "errored" ? "warning" : run.is_passed ? "success" : "danger"}
        />
      </div>

      {isRunning ? (
        <div className="space-y-2" role="status">
          <div className="flex items-center justify-between gap-3 text-sm text-ink-muted">
            <span className="flex items-center gap-2">
              <Spinner size="sm" /> {t("assistant.autotests.progress", { done: summary.done, total: summary.total })}
            </span>
            <span>{percent.format(summary.progress)}</span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-surface-muted"
            role="progressbar"
            aria-label={t("assistant.autotests.progressLabel")}
            aria-valuemin={0}
            aria-valuemax={summary.total}
            aria-valuenow={summary.done}
          >
            <div className="h-full rounded-full bg-accent-solid transition-[width]" style={{ width: `${Math.round(summary.progress * 100)}%` }} />
          </div>
          <p className="text-sm text-ink-subtle">{t("assistant.autotests.runningHint")}</p>
        </div>
      ) : (
        <p className="text-sm text-ink-muted">
          {t("assistant.autotests.ranAt", { date: format.dateTime(run.updated_at) })} {t("assistant.autotests.rule")}
        </p>
      )}

      {!isRunning && run.status === "errored" ? (
        <Alert
          tone="warning"
          title={t("assistant.autotests.erroredTitle")}
          action={
            canRun ? (
              <Button size="sm" variant="secondary" leadingIcon={<IconFlask className="size-4" aria-hidden />} onClick={onRun}>
                {t("assistant.autotests.runAgain")}
              </Button>
            ) : undefined
          }
        >
          {t("assistant.autotests.erroredDescription")}
        </Alert>
      ) : null}

      {!isRunning && run.status === "finished" && !run.is_full_coverage ? (
        <p className="text-sm text-ink-muted">{t("assistant.autotests.partialRun")}</p>
      ) : null}

      {!isRunning && run.status !== "errored" && summary.errored > 0 && summary.errored === summary.total ? (
        <Alert tone="warning" title={t("assistant.autotests.allErroredTitle")}>
          {t("assistant.autotests.allErroredDescription")}
        </Alert>
      ) : null}

      {run.results.length > 0 ? (
        <>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="flex flex-wrap gap-1 rounded-xl bg-surface-muted p-1" role="group" aria-label={t("assistant.autotests.filterLabel")}>
              {(["all", "problems"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={outcome === value}
                  onClick={() => setOutcome(value)}
                  className={cn(
                    "h-8 rounded-lg px-3 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-focus",
                    outcome === value ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink",
                  )}
                >
                  {value === "all"
                    ? t("assistant.autotests.filterAll", { count: run.results.length })
                    : t("assistant.autotests.filterProblems", { count: summary.failed + summary.errored })}
                </button>
              ))}
            </div>
            {languages.length > 1 ? (
              <label className="flex items-center gap-2 text-sm text-ink-muted">
                <span>{t("assistant.autotests.language")}</span>
                <Select value={language} onChange={(event) => setLanguage(event.target.value)} className="w-44">
                  <option value="all">{t("assistant.autotests.allLanguages")}</option>
                  {languages.map((tag) => (
                    <option key={tag} value={tag}>
                      {languageName(tag, locale)}
                    </option>
                  ))}
                </Select>
              </label>
            ) : null}
          </div>

          {visible.length === 0 ? (
            <p className="rounded-xl border border-line px-4 py-6 text-center text-sm text-ink-muted">{t("assistant.autotests.noProblems")}</p>
          ) : (
            <ul className="space-y-2">
              {visible.map((result) => (
                <ScenarioResult key={`${result.scenario_key}-${result.language}`} result={result} />
              ))}
            </ul>
          )}
        </>
      ) : null}

      {canRun && !isRunning ? (
        <div className="flex justify-end">
          <Button variant="secondary" leadingIcon={<IconFlask className="size-4" aria-hidden />} onClick={onRun}>
            {t("assistant.autotests.runAgain")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: BadgeTone }) {
  return (
    <div className="rounded-xl border border-line px-4 py-3">
      <p className="text-xs font-medium tracking-wide text-ink-subtle uppercase">{label}</p>
      <p
        className={cn(
          "mt-1 text-lg font-semibold",
          tone === "success" ? "text-success" : tone === "danger" ? "text-danger" : tone === "warning" ? "text-warning" : tone === "info" ? "text-info" : "text-ink",
        )}
      >
        {value}
      </p>
    </div>
  );
}

function ScenarioResult({ result }: { result: AutotestScenarioResult }) {
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
