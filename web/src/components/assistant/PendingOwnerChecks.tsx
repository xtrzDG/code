"use client";

/**
 * The owner's checks in "Apply changes" that customers' answers were not
 * checked against yet ("New check: “Can I come with my dog?”"), with what
 * each answer must do. The next update asks them first.
 */

import { useI18n } from "@/i18n/client";
import { expectationSentence, pendingCheckLine, type PendingOwnerCheck } from "@/lib/assistant/ownerChecks";

export function PendingOwnerChecks({ checks, labelId }: { checks: readonly PendingOwnerCheck[]; labelId: string }) {
  const translator = useI18n();
  return (
    <ul aria-labelledby={labelId} className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
      {checks.map((check) => (
        <li key={check.autotest_case_id} className="flex items-start gap-3 px-3 py-2.5 text-sm" data-pending-check={check.autotest_case_id}>
          <span
            aria-hidden
            className={check.action === "added" ? "mt-1.5 size-2 shrink-0 rounded-full bg-success" : "mt-1.5 size-2 shrink-0 rounded-full bg-accent-solid"}
          />
          <span className="min-w-0 [overflow-wrap:anywhere]">
            <span dir="auto" className="block text-ink">
              {pendingCheckLine(check, translator)}
            </span>
            <span dir="auto" className="block text-xs text-ink-subtle">
              {expectationSentence(check, translator)}
            </span>
          </span>
        </li>
      ))}
    </ul>
  );
}
