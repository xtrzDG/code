"use client";

import { formatLocalDateRange } from "@/components/insights/dates";
import { Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { conversationShare, type CustomerSources, type SourceTotals } from "@/components/value/sourcesModel";
import { useI18n } from "@/i18n/client";

import { SourceCell, sourceRowKey } from "./SourceCell";

/** The figures of a source, formatted: conversations, bookings, requests and what they are worth. */
export interface SourceFigures {
  number: (value: number) => string;
  money: (minor: number | null | undefined) => string;
  showsRequests: boolean;
}

/**
 * "Where customers came from" as a table (screens from a small tablet up):
 * a row per source, its numbers in columns, and the totals at the foot.
 */
export function CustomerSourcesTable({
  view,
  totals,
  figures,
}: {
  view: CustomerSources;
  totals: SourceTotals;
  figures: SourceFigures;
}) {
  const { t, locale } = useI18n();
  const { number, money, showsRequests } = figures;
  return (
    <Table caption={t("sources.caption", { range: formatLocalDateRange(view.date_from, view.date_to, locale) })}>
      <THead>
        <Tr className="hover:bg-transparent">
          <Th className="ps-5">{t("sources.columns.source")}</Th>
          <Th align="right">{t("sources.columns.conversations")}</Th>
          <Th align="right">{t("sources.columns.bookings")}</Th>
          {showsRequests ? <Th align="right">{t("sources.columns.requests")}</Th> : null}
          <Th align="right" className="pe-5">
            {t("sources.columns.value")}
          </Th>
        </Tr>
      </THead>
      <TBody>
        {(view.rows ?? []).map((row) => (
          <Tr key={sourceRowKey(row)}>
            <Th scope="row" className="min-w-44 ps-5 align-top font-normal whitespace-normal">
              <SourceCell row={row} share={conversationShare(row, totals)} />
            </Th>
            <Td align="right" className="tabular-nums">
              {number(row.conversation_count)}
            </Td>
            <Td align="right" className="tabular-nums">
              {number(row.booking_count)}
            </Td>
            {showsRequests ? (
              <Td align="right" className="tabular-nums">
                {number(row.request_count)}
              </Td>
            ) : null}
            <Td align="right" className="pe-5 whitespace-nowrap tabular-nums">
              {money(row.estimated_value_minor)}
            </Td>
          </Tr>
        ))}
      </TBody>
      <tfoot className="border-t border-line-strong/40 text-sm font-semibold text-ink">
        <tr>
          <Th scope="row" className="ps-5">
            {t("sources.total")}
          </Th>
          <Td align="right" className="font-semibold tabular-nums">
            {number(totals.conversations)}
          </Td>
          <Td align="right" className="font-semibold tabular-nums">
            {number(totals.bookings)}
          </Td>
          {showsRequests ? (
            <Td align="right" className="font-semibold tabular-nums">
              {number(totals.requests)}
            </Td>
          ) : null}
          <Td align="right" className="pe-5 font-semibold whitespace-nowrap tabular-nums">
            {money(totals.valueMinor)}
          </Td>
        </tr>
      </tfoot>
    </Table>
  );
}
