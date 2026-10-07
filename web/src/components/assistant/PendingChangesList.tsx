"use client";

/**
 * The changes customers do not get yet, grouped by the part of the
 * business they touch ("Offer and prices: Price of “Khachapuri”: 18,00 ₾
 * → 20,00 ₾"). Owners' own titles are user content in their own direction (`UserSentence`).
 */

import { UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { describeChange, groupChanges, type PendingChange } from "@/lib/assistant/pendingChanges";

export function PendingChangesList({ changes, labelId }: { changes: readonly PendingChange[]; labelId: string }) {
  const translator = useI18n();
  const { t } = translator;

  return (
    <div aria-labelledby={labelId} role="group" className="space-y-4">
      {groupChanges(changes).map((group) => (
        <section key={group.area} className="space-y-1.5">
          <h3 className="text-xs font-medium text-ink-subtle">{t(`applyChanges.areas.${group.area}`)}</h3>
          <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
            {group.changes.map((change, index) => (
              <li
                key={`${change.action}-${change.subject ?? change.field ?? change.link_kind ?? change.weekday ?? change.date ?? ""}-${index}`}
                className="flex items-start gap-3 px-3 py-2.5 text-sm text-ink"
              >
                <span
                  aria-hidden
                  className={
                    change.action === "added"
                      ? "mt-1.5 size-2 shrink-0 rounded-full bg-success"
                      : change.action === "removed"
                        ? "mt-1.5 size-2 shrink-0 rounded-full bg-danger"
                        : "mt-1.5 size-2 shrink-0 rounded-full bg-accent-solid"
                  }
                />
                <span dir="auto" className="min-w-0 [overflow-wrap:anywhere]">
                  <UserSentence {...describeChange(change, translator)} />
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
