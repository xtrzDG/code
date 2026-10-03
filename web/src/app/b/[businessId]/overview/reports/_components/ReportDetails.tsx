"use client";

import { formatLocalDateRange } from "@/components/insights/dates";
import { Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { DeltaChip } from "@/components/value/DeltaChip";
import { formatWholeMoney, periodDays, type ValueReport } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import { splitMinutes, visibleRows, type RowKind } from "../_lib/reportsModel";

/**
 * Every number of a stored report next to the period before and the
 * change, and how the money was estimated.
 */
export function ReportDetails({ report }: { report: ValueReport }) {
  const { t, locale } = useI18n();
  const days = periodDays(report.date_from, report.date_to);

  const show = (value: number | null | undefined, kind: RowKind): string => {
    if (value === null || value === undefined) {
      return "–";
    }
    if (kind === "money") {
      return formatWholeMoney(value, report.currency_code, locale);
    }
    if (kind === "minutes") {
      const parts = splitMinutes(value);
      return parts.hours > 0
        ? t("reports.duration.hoursMinutes", { hours: formatNumber(parts.hours, locale), minutes: formatNumber(parts.minutes, locale) })
        : t("reports.duration.minutes", { minutes: formatNumber(parts.minutes, locale) });
    }
    return formatNumber(value, locale);
  };

  return (
    <div className="space-y-3">
      <Table caption={t("reports.details.caption")}>
        <THead>
          <Tr>
            <Th>{t("reports.details.measure")}</Th>
            <Th align="right">{formatLocalDateRange(report.date_from, report.date_to, locale)}</Th>
            <Th align="right">{formatLocalDateRange(report.previous_date_from, report.previous_date_to, locale)}</Th>
            <Th align="right">{t("reports.details.change")}</Th>
          </Tr>
        </THead>
        <TBody>
          {visibleRows(report.current, report.previous).map((row) => (
            <Tr key={row.field}>
              <Th scope="row" className="font-normal whitespace-normal text-ink">
                {t(row.label)}
              </Th>
              <Td align="right" className="font-medium tabular-nums">
                {show(report.current[row.field], row.kind)}
              </Td>
              <Td align="right" className="text-ink-muted tabular-nums">
                {show(report.previous[row.field], row.kind)}
              </Td>
              <Td align="right">
                <DeltaChip
                  current={report.current[row.field] ?? 0}
                  previous={report.previous[row.field] ?? 0}
                  days={days}
                  polarity={row.polarity}
                />
              </Td>
            </Tr>
          ))}
        </TBody>
      </Table>
      <p className="text-xs text-ink-subtle">
        {report.average_check_minor === null || report.average_check_minor === undefined
          ? t("reports.details.noCheck")
          : t(report.average_check_source === "owner" ? "reports.details.ownerCheck" : "reports.details.typicalCheck", {
              money: formatWholeMoney(report.average_check_minor, report.currency_code, locale),
            })}
      </p>
    </div>
  );
}
