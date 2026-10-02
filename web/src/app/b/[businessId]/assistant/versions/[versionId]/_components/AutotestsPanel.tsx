"use client";

import { useState } from "react";

import { IconFlask } from "@/components/content/icons";
import { Alert, Button, EmptyState, Select, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import {
  filterResults,
  resultLanguages,
  sortResults,
  summarizeRun,
  type AutotestRunView,
  type ResultFilter,
} from "@/lib/assistant/autotests";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";

import { RunSummary } from "./RunSummary";
import { ScenarioResult } from "./ScenarioResult";

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

  return (
    <div className="space-y-5">
      <RunSummary run={run} isRunning={isRunning} />

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
