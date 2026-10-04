"use client";

/** The first wins the business reached, under the guide: what and when. */

import type { Schema } from "@/api/types";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconStar } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

type Milestone = Schema<"ActivationMilestoneView">;

const WIN_LABELS: Partial<Record<Milestone["kind"], MessageKey>> = {
  first_conversation: "setupGuide.wins.first_conversation",
  first_booking: "setupGuide.wins.first_booking",
  first_after_hours_booking: "setupGuide.wins.first_after_hours_booking",
};

export function GuideWins({ wins }: { wins: readonly Milestone[] }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  return (
    <div className="mt-4 border-t border-line pt-4">
      <h3 className="text-xs font-semibold tracking-wide text-ink-muted uppercase">{t("setupGuide.wins.title")}</h3>
      <ul className="mt-2 flex flex-wrap gap-2">
        {wins.map((win) => {
          const label = WIN_LABELS[win.kind];
          return label ? (
            <li key={win.kind} className="inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-3 py-1 text-xs text-accent-ink">
              <IconStar className="size-3.5" aria-hidden />
              <span className="font-medium">{t(label)}</span>
              <span className="text-ink-muted">· {format.date(win.occurred_at)}</span>
            </li>
          ) : null;
        })}
      </ul>
    </div>
  );
}
