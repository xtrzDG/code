"use client";

import { conversationShare, type CustomerSources, type SourceTotals } from "@/components/value/sourcesModel";
import { useI18n } from "@/i18n/client";

import type { SourceFigures } from "./CustomerSourcesTable";
import { SourceCell, sourceRowKey } from "./SourceCell";

/**
 * "Where customers came from" on a phone: a source per item, its numbers
 * under its name (labelled, as a table's columns would not fit), and the
 * totals last.
 */
export function CustomerSourcesList({
  view,
  totals,
  figures,
}: {
  view: CustomerSources;
  totals: SourceTotals;
  figures: SourceFigures;
}) {
  const { t } = useI18n();
  return (
    <ul className="divide-y divide-line">
      {(view.rows ?? []).map((row) => (
        <li key={sourceRowKey(row)} className="space-y-2.5 px-5 py-3.5">
          <SourceCell row={row} share={conversationShare(row, totals)} />
          <Figures
            figures={figures}
            conversations={row.conversation_count}
            bookings={row.booking_count}
            requests={row.request_count}
            valueMinor={row.estimated_value_minor}
          />
        </li>
      ))}
      <li className="space-y-2.5 bg-surface-muted/40 px-5 py-3.5">
        <p className="text-sm font-semibold text-ink">{t("sources.total")}</p>
        <Figures
          figures={figures}
          conversations={totals.conversations}
          bookings={totals.bookings}
          requests={totals.requests}
          valueMinor={totals.valueMinor}
        />
      </li>
    </ul>
  );
}

function Figures({
  figures,
  conversations,
  bookings,
  requests,
  valueMinor,
}: {
  figures: SourceFigures;
  conversations: number;
  bookings: number;
  requests: number;
  valueMinor: number | null | undefined;
}) {
  const { t } = useI18n();
  const { number, money, showsRequests } = figures;
  const items = [
    { label: t("sources.columns.conversations"), value: number(conversations) },
    { label: t("sources.columns.bookings"), value: number(bookings) },
    ...(showsRequests ? [{ label: t("sources.columns.requests"), value: number(requests) }] : []),
    { label: t("sources.columns.value"), value: money(valueMinor) },
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-3 gap-y-2">
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-xs break-words text-ink-muted">{item.label}</dt>
          <dd className="text-sm font-medium whitespace-nowrap text-ink tabular-nums">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
