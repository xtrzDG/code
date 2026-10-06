"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";

import { RECENT_LABELS, recentCounts, type CampaignSettingsView } from "../_lib/returnVisitsModel";

const ORDER = ["sent", "booked", "skipped"] as const;

/** The last 30 days in three numbers: messages sent, customers who booked again, messages not sent. */
export function RecentCampaignCounts({ view }: { view: CampaignSettingsView }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const counts = recentCounts(view);
  return (
    <section aria-labelledby="return-visits-recent" className="rounded-2xl border border-line bg-surface p-4 sm:p-5">
      <h2 id="return-visits-recent" className="text-sm font-semibold tracking-wide text-ink-muted uppercase">
        {t("returnVisits.recent.title")}
      </h2>
      <dl className="mt-3 grid grid-cols-3 gap-3">
        {ORDER.map((status) => (
          <div key={status} className="min-w-0">
            <dt className="text-xs text-ink-muted">{t(RECENT_LABELS[status])}</dt>
            <dd className={status === "booked" ? "text-2xl font-semibold text-accent tabular-nums" : "text-2xl font-semibold text-ink tabular-nums"}>
              {format.number(counts[status])}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
