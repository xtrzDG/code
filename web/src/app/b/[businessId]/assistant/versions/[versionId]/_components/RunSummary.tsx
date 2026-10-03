"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Spinner, type BadgeTone } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatScore, scoreTone, summarizeRun, type AutotestRunView } from "@/lib/assistant/autotests";
import { cn } from "@/lib/cn";

/** A run at a glance: passed scenarios, the average score and the result; progress while it runs. */
export function RunSummary({ run, isRunning }: { run: AutotestRunView; isRunning: boolean }) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const summary = summarizeRun(run);
  const percent = new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 0 });
  return (
    <>
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
      <div className="space-y-1 text-sm text-ink-muted">
        <p>{t("assistant.autotests.ranAt", { date: format.dateTime(run.updated_at) })}</p>
        <p>{t("assistant.autotests.rule")}</p>
      </div>
    )}
    </>
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
