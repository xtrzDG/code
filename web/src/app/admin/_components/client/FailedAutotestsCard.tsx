"use client";

import type { Schema } from "@/api/types";
import { Badge, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { CHECK_CODE_LABELS, CRITERION_LABELS, OUTCOME_LABELS, SCENARIO_LABELS } from "../labels";

type FailedAutotest = Schema<"FailedAutotestView">;

/**
 * Why one scenario failed, in the reader's language: the harness checks
 * that failed and the judge's low criteria. The judge's own notes are
 * English text, so outside English they wait behind a disclosure.
 */
function FailureReasons({ test }: { test: FailedAutotest }) {
  const { t, locale } = useI18n();
  const codes = test.check_codes ?? [];
  const criteria = test.low_criteria ?? [];
  const notes = test.judge_notes ?? [];
  const noteList = (
    <ul lang="en" className="list-disc space-y-0.5 ps-5 text-sm text-ink-muted">
      {notes.map((note, index) => (
        <li key={index} dir="auto">
          {note}
        </li>
      ))}
    </ul>
  );
  return (
    <>
      {codes.length > 0 || criteria.length > 0 ? (
        <ul className="list-disc space-y-0.5 ps-5 text-sm text-ink">
          {codes.map((code) => (
            <li key={code}>{t(CHECK_CODE_LABELS[code])}</li>
          ))}
          {criteria.length > 0 ? (
            <li>{t("admin.detail.lowCriteria", { criteria: criteria.map((criterion) => t(CRITERION_LABELS[criterion])).join(", ") })}</li>
          ) : null}
        </ul>
      ) : null}
      {notes.length === 0 ? null : locale === "en" ? (
        noteList
      ) : (
        <details className="text-sm">
          <summary className="cursor-pointer text-ink-subtle">{t("admin.detail.judgeNotes")}</summary>
          <div className="mt-1">{noteList}</div>
        </details>
      )}
    </>
  );
}

/** The autotests the client's active version failed in its verdict run, and why. */
export function FailedAutotestsCard({ tests }: { tests: FailedAutotest[] }) {
  const { t } = useI18n();
  return (
    <Card title={t("admin.detail.autotestsTitle")} padded={tests.length === 0}>
      {tests.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("admin.detail.noFailedTests")}</p>
      ) : (
        <ul className="divide-y divide-line">
          {tests.map((test) => (
            <li key={`${test.scenario_key}-${test.language}`} className="space-y-1.5 px-5 py-4 sm:px-6">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-ink">{t(SCENARIO_LABELS[test.kind])}</span>
                <Badge tone={test.outcome === "errored" ? "warning" : "danger"}>{t(OUTCOME_LABELS[test.outcome])}</Badge>
                <Badge>{test.language}</Badge>
                <code className="text-xs text-ink-subtle">{test.scenario_key}</code>
              </div>
              <FailureReasons test={test} />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
