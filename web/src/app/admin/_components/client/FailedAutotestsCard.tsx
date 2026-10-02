"use client";

import type { Schema } from "@/api/types";
import { Badge, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { OUTCOME_LABELS, SCENARIO_LABELS } from "../labels";

/** The autotests the client's assistant failed, with the judge's notes. */
export function FailedAutotestsCard({ tests }: { tests: Schema<"FailedAutotestView">[] }) {
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
              {(test.judge_notes ?? []).length > 0 ? (
                <ul className="list-disc space-y-0.5 pl-5 text-sm text-ink-muted">
                  {(test.judge_notes ?? []).map((note, index) => (
                    <li key={index} dir="auto">
                      {note}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
