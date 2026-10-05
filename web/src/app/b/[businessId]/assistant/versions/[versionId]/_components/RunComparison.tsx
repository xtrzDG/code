"use client";

import type { ReactNode } from "react";

import { IconCheckCircle, IconXCircle } from "@/components/icons";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  changeTone,
  formatScoreChange,
  hasComparisonChanges,
  scoreDrops,
  scoreRises,
  type AutotestOutcomeChange,
  type AutotestRunComparison,
  type AutotestScoreChange,
} from "@/lib/assistant/autotestComparison";
import { formatScore, type AutotestOutcome, type JudgeCriterion } from "@/lib/assistant/autotests";
import { languageName } from "@/lib/format";

import { SCENARIO_KIND_LABELS } from "../_lib/scenarioLabels";

const OUTCOME_LABELS: Record<AutotestOutcome, MessageKey> = {
  passed: "assistant.autotests.outcomes.passed",
  failed: "assistant.autotests.outcomes.failed",
  errored: "assistant.autotests.outcomes.errored",
};

const CRITERION_LABELS: Record<JudgeCriterion, MessageKey> = {
  facts_and_prices: "assistant.autotests.criteria.facts_and_prices",
  booking_data: "assistant.autotests.criteria.booking_data",
  ai_disclosure: "assistant.autotests.criteria.ai_disclosure",
  handoff: "assistant.autotests.criteria.handoff",
  language: "assistant.autotests.criteria.language",
};

/**
 * A finished run against the run of the update that was live when it
 * started: new problems first, then the scores that fell, the fixes and the
 * scores that rose (only scenarios both runs played).
 */
export function RunComparison({ comparison }: { comparison: AutotestRunComparison }) {
  const { t, locale } = useI18n();
  const score = (value: number) => formatScore(value, locale);
  const scenarioName = (change: Pick<AutotestOutcomeChange, "kind" | "language">) =>
    t("assistant.comparison.scenario", { name: t(SCENARIO_KIND_LABELS[change.kind]), language: languageName(change.language, locale) });
  const drops = scoreDrops(comparison);
  const rises = scoreRises(comparison);
  const averageChange = comparison.average_score_change;

  return (
    <section data-run-comparison aria-labelledby="run-comparison-title" className="space-y-4 rounded-xl border border-line px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 id="run-comparison-title" className="text-sm font-semibold text-ink">
            {t("assistant.comparison.title", { number: comparison.baseline_version_number })}
          </h3>
          <p className="text-sm text-ink-muted">
            {t("assistant.comparison.description")} {t("assistant.comparison.shared", { count: comparison.shared_scenario_count })}
          </p>
        </div>
        {averageChange !== null && averageChange !== undefined && comparison.baseline_average_score !== null && comparison.baseline_average_score !== undefined ? (
          <div className="text-right">
            <p className="text-xs text-ink-subtle">{t("assistant.comparison.averageScore")}</p>
            <p className="flex items-center justify-end gap-2">
              <Badge tone={changeTone(averageChange)}>{formatScoreChange(averageChange, locale)}</Badge>
              <span className="text-xs text-ink-muted">{t("assistant.comparison.averageWas", { score: score(comparison.baseline_average_score) })}</span>
            </p>
          </div>
        ) : null}
      </div>

      {comparison.shared_scenario_count === 0 ? (
        <p className="text-sm text-ink-muted">{t("assistant.comparison.noShared")}</p>
      ) : !hasComparisonChanges(comparison) ? (
        <p className="flex items-center gap-2 text-sm text-ink-muted">
          <IconCheckCircle className="size-4 shrink-0 text-success" aria-hidden />
          {t("assistant.comparison.noChanges")}
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {comparison.new_failures.length > 0 ? (
            <ChangeList title={t("assistant.comparison.newFailures")} hint={t("assistant.comparison.newFailuresHint")} tone="danger">
              {comparison.new_failures.map((change) => (
                <li key={`${change.scenario_key}-${change.language}`} className="flex items-start gap-2">
                  <IconXCircle className="mt-0.5 size-4 shrink-0 text-danger" aria-hidden />
                  <span className="min-w-0">
                    <span className="block text-ink">{scenarioName(change)}</span>
                    <span className="block text-xs text-ink-subtle">
                      {t("assistant.comparison.outcomeMove", { from: t(OUTCOME_LABELS[change.baseline_outcome]), to: t(OUTCOME_LABELS[change.outcome]) })}
                    </span>
                  </span>
                </li>
              ))}
            </ChangeList>
          ) : null}
          {drops.length > 0 ? <ScoreList title={t("assistant.comparison.scoreDrops")} changes={drops} name={scenarioName} /> : null}
          {comparison.fixed.length > 0 ? (
            <ChangeList title={t("assistant.comparison.fixed")} hint={t("assistant.comparison.fixedHint")} tone="success">
              {comparison.fixed.map((change) => (
                <li key={`${change.scenario_key}-${change.language}`} className="flex items-start gap-2">
                  <IconCheckCircle className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
                  <span className="text-ink">{scenarioName(change)}</span>
                </li>
              ))}
            </ChangeList>
          ) : null}
          {rises.length > 0 ? <ScoreList title={t("assistant.comparison.scoreRises")} changes={rises} name={scenarioName} /> : null}
          {comparison.criterion_changes.length > 0 ? (
            <ChangeList title={t("assistant.comparison.criteria")}>
              {comparison.criterion_changes.map((change) => (
                <ScoreRow
                  key={change.criterion}
                  label={t(CRITERION_LABELS[change.criterion])}
                  from={change.baseline_average_score}
                  to={change.average_score}
                  change={change.change}
                />
              ))}
            </ChangeList>
          ) : null}
        </div>
      )}
    </section>
  );
}

function ChangeList({ title, hint, tone, children }: { title: string; hint?: string; tone?: "danger" | "success"; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <h4 className={tone === "danger" ? "text-xs font-semibold tracking-wide text-danger uppercase" : "text-xs font-semibold tracking-wide text-ink-muted uppercase"}>
        {title}
      </h4>
      {hint ? <p className="mt-0.5 text-xs text-ink-subtle">{hint}</p> : null}
      <ul className="mt-2 space-y-2 text-sm">{children}</ul>
    </div>
  );
}

function ScoreList({
  title,
  changes,
  name,
}: {
  title: string;
  changes: readonly AutotestScoreChange[];
  name: (change: AutotestScoreChange) => string;
}) {
  return (
    <ChangeList title={title}>
      {changes.map((change) => (
        <ScoreRow
          key={`${change.scenario_key}-${change.language}`}
          label={name(change)}
          from={change.baseline_average_score}
          to={change.average_score}
          change={change.change}
        />
      ))}
    </ChangeList>
  );
}

function ScoreRow({ label, from, to, change }: { label: string; from: number; to: number; change: number }) {
  const { t, locale } = useI18n();
  return (
    <li className="flex items-center justify-between gap-3">
      <span className="min-w-0 text-ink">{label}</span>
      <span className="flex shrink-0 items-center gap-2 tabular-nums">
        <span className="text-xs text-ink-muted">
          {t("assistant.comparison.scoreMove", { from: formatScore(from, locale), to: formatScore(to, locale) })}
        </span>
        <Badge tone={changeTone(change)}>{formatScoreChange(change, locale)}</Badge>
      </span>
    </li>
  );
}
