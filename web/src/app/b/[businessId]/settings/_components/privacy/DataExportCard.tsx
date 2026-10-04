"use client";

import { useEffect, useId, useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { CSV_TABLES } from "@/components/exports/csvExport";
import { useCsvExport } from "@/components/exports/useCsvExport";
import { IconDownload, IconFile, IconShield } from "@/components/icons";
import { RefreshFailed } from "@/components/insights/common";
import { Button, Card, ErrorState, LoadingRegion, SkeletonRows } from "@/components/ui";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";

import { useBusinessExports } from "../../_lib/useBusinessExports";
import { BusinessExportRow } from "./BusinessExportRow";

const MINUTE_MS = 60_000;

/**
 * Settings → Privacy → "Export your data": the full export of the
 * business (a ZIP the worker builds, its signed link for 24 hours) and
 * each table of the cabinet as CSV. Owners only: staff see why not.
 */
export function DataExportCard() {
  const { t } = useI18n();
  const { isOwner } = useBusiness();
  const { exports, items, isWorking, begin, isStarting } = useBusinessExports({ enabled: isOwner });
  const csv = useCsvExport();
  const historyId = useId();
  const tablesId = useId();
  // Links run out while the page stays open: the rows look at the clock every minute.
  const [nowUs, setNowUs] = useState(() => Date.now() * 1000);
  useEffect(() => {
    const timer = window.setInterval(() => setNowUs(Date.now() * 1000), MINUTE_MS);
    return () => window.clearInterval(timer);
  }, []);

  if (!isOwner || exports.error?.code === "access_denied") {
    return (
      <Card title={t("dataExports.full.title")}>
        <OwnerOnlyState className="py-4" />
      </Card>
    );
  }

  return (
    <Card title={t("dataExports.full.title")} description={t("dataExports.full.description")}>
      <div className="space-y-8">
        <div className="space-y-4">
          <Button
            leadingIcon={<IconFile className="size-4" aria-hidden />}
            isLoading={isStarting}
            disabled={isWorking}
            onClick={() => void begin()}
          >
            {t("dataExports.full.start")}
          </Button>
          {isWorking ? (
            <p className="text-sm text-ink-muted" role="status">
              {t("dataExports.full.working")}
            </p>
          ) : null}
          <p className="flex max-w-3xl gap-2 text-xs text-ink-subtle">
            <IconShield className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span>
              {t("dataExports.full.linkNote")} {t("dataExports.full.erasedNote")}
            </span>
          </p>

          <section aria-labelledby={historyId} className="space-y-2">
            <h3 id={historyId} className="text-sm font-semibold text-ink">
              {t("dataExports.full.history")}
            </h3>
            {exports.error && items === undefined ? (
              <ErrorState error={exports.error} onRetry={exports.reload} className="py-4" />
            ) : items === undefined ? (
              <LoadingRegion label={t("common.loading")}>
                <SkeletonRows rows={2} />
              </LoadingRegion>
            ) : items.length === 0 ? (
              <p className="text-sm text-ink-muted">{t("dataExports.full.empty")}</p>
            ) : (
              <>
                {exports.error ? <RefreshFailed error={exports.error} onRetry={exports.reload} /> : null}
                <ul className="divide-y divide-line rounded-xl border border-line" aria-live="polite">
                  {items.map((item) => (
                    <BusinessExportRow key={item.id} item={item} nowUs={nowUs} />
                  ))}
                </ul>
              </>
            )}
          </section>
        </div>

        <section aria-labelledby={tablesId} className="space-y-3 border-t border-line pt-6">
          <div className="space-y-1">
            <h3 id={tablesId} className="text-sm font-semibold text-ink">
              {t("dataExports.tables.title")}
            </h3>
            <p className="max-w-3xl text-sm text-ink-muted">{t("dataExports.tables.description")}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {CSV_TABLES.map((table) => {
              const name = t(`dataExports.csv.tables.${table}`);
              return (
                <Button
                  key={table}
                  variant="secondary"
                  size="sm"
                  isLoading={csv.exporting === table}
                  disabled={csv.exporting !== null && csv.exporting !== table}
                  leadingIcon={<IconDownload className="size-4" aria-hidden />}
                  aria-label={t("dataExports.csv.tableLabel", { table: name })}
                  onClick={() => void csv.download(table)}
                >
                  {name}
                </Button>
              );
            })}
          </div>
        </section>
      </div>
    </Card>
  );
}
