"use client";

import { Card, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { dateTimeFormat } from "@/lib/intl/formatters";

import { cohortColumns, cohortShade, type CohortRowView } from "../../_lib/metrics";
import { ScrollingTable } from "./ScrollingTable";
import type { MetricsFormat } from "./useMetricsFormat";

/**
 * Sign-up cohorts as a grid: a row per month, a column per month since,
 * each cell the share of the cohort with a paying business. The number is
 * always printed; the accent behind it only makes the pattern easy to see.
 * Months that have not come yet stay empty.
 */
export function CohortGrid({ rows, format }: { rows: readonly CohortRowView[]; format: MetricsFormat }) {
  const { t, locale } = useI18n();
  const title = t("adminMetrics.cohorts.title");
  const columns = cohortColumns(rows);
  const monthName = (month: string) =>
    dateTimeFormat(locale, { month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${month}-01T00:00:00Z`));

  return (
    <Card title={title} description={t("adminMetrics.cohorts.description")} padded={false} aria-label={title}>
      {rows.length === 0 ? (
        <p className="p-5 text-sm text-ink-muted">{t("adminMetrics.cohorts.empty")}</p>
      ) : (
        <ScrollingTable caption={title}>
          <THead>
            <Tr>
              <Th>{t("adminMetrics.cohorts.month")}</Th>
              <Th align="right">{t("adminMetrics.cohorts.signUps")}</Th>
              <Th align="right">{t("adminMetrics.cohorts.wentLive")}</Th>
              {Array.from({ length: columns }, (_, offset) => (
                <Th key={offset} align="center" className="px-2">
                  <abbr title={t("adminMetrics.cohorts.offsetLabel", { offset })} className="no-underline">
                    {t("adminMetrics.cohorts.offset", { offset })}
                  </abbr>
                </Th>
              ))}
            </Tr>
          </THead>
          <TBody>
            {rows.map((row) => (
              <Tr key={row.month}>
                <Th scope="row" className="font-normal whitespace-nowrap text-ink">
                  {monthName(row.month)}
                </Th>
                <Td align="right" className="tabular-nums">
                  {format.number(row.sign_ups)}
                </Td>
                <Td align="right" className="tabular-nums">
                  {format.number(row.went_live)}
                </Td>
                {Array.from({ length: columns }, (_, offset) => {
                  const share = row.paying?.[offset];
                  return share === undefined ? (
                    <Td key={offset} className="px-1 py-1" />
                  ) : (
                    <Td key={offset} align="center" className="px-1 py-1">
                      <span
                        className={cn("block min-w-12 rounded-md px-1.5 py-1.5 text-xs text-ink tabular-nums", cohortShade(share))}
                        title={t("adminMetrics.cohorts.cell", {
                          month: monthName(row.month),
                          offset,
                          percent: format.percent(share),
                        })}
                      >
                        {format.percent(share)}
                      </span>
                    </Td>
                  );
                })}
              </Tr>
            ))}
          </TBody>
        </ScrollingTable>
      )}
    </Card>
  );
}
