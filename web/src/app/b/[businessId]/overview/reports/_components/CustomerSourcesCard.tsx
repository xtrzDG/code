"use client";

import Link from "next/link";
import { useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import { IconTag } from "@/components/icons";
import { Card, EmptyState, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { DEFAULT_SOURCE_PERIOD, hasTaggedSources, SOURCE_PERIODS, sourceTotals, type SourcePeriod } from "@/components/value/sourcesModel";
import { useCustomerSources } from "@/components/value/useValueQueries";
import { formatWholeMoney } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { CustomerSourcesList } from "./CustomerSourcesList";
import { CustomerSourcesTable, type SourceFigures } from "./CustomerSourcesTable";

/**
 * Reports → "Where customers came from" (owners): per link, QR code, ad and
 * phone line of the period, the conversations started, the bookings and
 * requests they brought and what those are worth in the value model.
 * Conversations without a tag are split by channel; the smallest tags are
 * folded into one row.
 */
export function CustomerSourcesCard() {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const [period, setPeriod] = useState<SourcePeriod>(DEFAULT_SOURCE_PERIOD);
  const sources = useCustomerSources(business.id, period);
  const view = sources.data;
  const rows = view?.rows ?? [];
  const totals = sourceTotals(rows);
  const showsRequests = view?.value_basis === "requests" || totals.requests > 0;
  const money = (minor: number | null | undefined) =>
    minor === null || minor === undefined || !view ? t("sources.noValue") : formatWholeMoney(minor, view.currency_code, locale);
  const number = (value: number) => formatNumber(value, locale);
  const figures: SourceFigures = { number, money, showsRequests };

  return (
    <Card
      padded={false}
      aria-label={t("sources.title")}
      title={
        <span className="flex items-center gap-2">
          <IconTag className="size-4 text-accent" aria-hidden />
          {t("sources.title")}
        </span>
      }
      description={t("sources.description")}
      actions={
        <SegmentedControl
          label={t("sources.periodLabel")}
          value={period}
          onChange={setPeriod}
          options={SOURCE_PERIODS.map((value) => ({ value, label: t(`sources.periods.${value}`) }))}
        />
      }
    >
      {sources.error && !view ? (
        <ErrorState error={sources.error} onRetry={sources.reload} className="py-6" />
      ) : !view ? (
        <LoadingRegion label={t("sources.loading")} className="p-5">
          <SkeletonText lines={5} />
        </LoadingRegion>
      ) : rows.length === 0 ? (
        <EmptyState title={t("sources.empty.title")} description={t("sources.empty.description")} />
      ) : (
        <div className={sources.isPlaceholder ? "opacity-60 transition-opacity" : "transition-opacity"}>
          <div className="hidden sm:block">
            <CustomerSourcesTable view={view} totals={totals} figures={figures} />
          </div>
          <div className="sm:hidden">
            <CustomerSourcesList view={view} totals={totals} figures={figures} />
          </div>
          {hasTaggedSources(rows) ? null : (
            <p className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-line px-5 py-3.5 text-xs text-ink-muted">
              <span>{t("sources.tagHint")}</span>
              <Link href={`${businessPath(business.id, "assistant/channels")}#share`} className="font-medium text-accent hover:underline">
                {t("sources.tagLink")}
              </Link>
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
