"use client";

import { Badge, Card, TBody, Td, Th, THead, Tr, type BadgeTone } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { payingShare, type SourceRowView, type WebVitalView } from "../../_lib/metrics";
import { ScrollingTable } from "./ScrollingTable";
import type { MetricsFormat } from "./useMetricsFormat";

const KNOWN_SOURCES = new Set(["direct", "unknown", "referral", "hosted_chat"]);

/** A source key in words when it is one of the platform's own; campaigns stay as written. */
export function useSourceName() {
  const { t } = useI18n();
  return (source: string) =>
    KNOWN_SOURCES.has(source) ? t(`adminMetrics.sources.names.${source as "direct" | "unknown" | "referral" | "hosted_chat"}`) : source;
}

/** Owners per acquisition source: sign-ups, went live, paying today. */
export function SourcesCard({ rows, format }: { rows: readonly SourceRowView[]; format: MetricsFormat }) {
  const { t } = useI18n();
  const sourceName = useSourceName();
  const title = t("adminMetrics.sources.title");
  return (
    <Card title={title} description={t("adminMetrics.sources.description")} padded={false} aria-label={title}>
      {rows.length === 0 ? (
        <p className="p-5 text-sm text-ink-muted">{t("adminMetrics.sources.empty")}</p>
      ) : (
        <ScrollingTable caption={title}>
          <THead>
            <Tr>
              <Th>{t("adminMetrics.sources.source")}</Th>
              <Th>{t("adminMetrics.sources.referralCode")}</Th>
              <Th align="right">{t("adminMetrics.sources.signUps")}</Th>
              <Th align="right">{t("adminMetrics.sources.wentLive")}</Th>
              <Th align="right">{t("adminMetrics.sources.paying")}</Th>
              <Th align="right">{t("adminMetrics.sources.payingShare")}</Th>
            </Tr>
          </THead>
          <TBody>
            {rows.map((row) => (
              <Tr key={`${row.source}:${row.referral_code ?? ""}`}>
                <Th scope="row" className="font-normal break-all text-ink">
                  {sourceName(row.source)}
                </Th>
                <Td className="font-mono text-xs break-all text-ink-muted">{row.referral_code ?? "—"}</Td>
                <Td align="right" className="tabular-nums">
                  {format.number(row.sign_ups)}
                </Td>
                <Td align="right" className="tabular-nums">
                  {format.number(row.went_live)}
                </Td>
                <Td align="right" className="tabular-nums">
                  {format.number(row.paying)}
                </Td>
                <Td align="right" className="tabular-nums">
                  {format.percent(payingShare(row))}
                </Td>
              </Tr>
            ))}
          </TBody>
        </ScrollingTable>
      )}
    </Card>
  );
}

const RATING_TONES: Record<WebVitalView["rating"], BadgeTone> = {
  good: "success",
  needs_improvement: "warning",
  poor: "danger",
};

/** The 75th percentile of each vital per page and device, busiest pages first. */
export function WebVitalsCard({ rows, format }: { rows: readonly WebVitalView[]; format: MetricsFormat }) {
  const { t } = useI18n();
  const title = t("adminMetrics.vitals.title");
  return (
    <Card title={title} description={t("adminMetrics.vitals.description")} padded={false} aria-label={title}>
      {rows.length === 0 ? (
        <p className="p-5 text-sm text-ink-muted">{t("adminMetrics.vitals.empty")}</p>
      ) : (
        <ScrollingTable caption={title}>
          <THead>
            <Tr>
              <Th>{t("adminMetrics.vitals.page")}</Th>
              <Th>{t("adminMetrics.vitals.metric")}</Th>
              <Th>{t("adminMetrics.vitals.device")}</Th>
              <Th align="right">{t("adminMetrics.vitals.p75")}</Th>
              <Th align="right">{t("adminMetrics.vitals.samples")}</Th>
              <Th>{t("adminMetrics.vitals.rating")}</Th>
            </Tr>
          </THead>
          <TBody>
            {rows.map((row) => (
              <Tr key={`${row.metric}:${row.route}:${row.device_class}`}>
                <Th scope="row" className="font-mono text-xs font-normal break-all text-ink">
                  {row.route}
                </Th>
                <Td>{t(`adminMetrics.vitals.metrics.${row.metric}`)}</Td>
                <Td>{t(`adminMetrics.vitals.devices.${row.device_class}`)}</Td>
                <Td align="right" className="whitespace-nowrap tabular-nums">
                  {format.vital(row)}
                </Td>
                <Td align="right" className="tabular-nums">
                  {format.number(row.samples)}
                </Td>
                <Td>
                  <Badge tone={RATING_TONES[row.rating]}>{t(`adminMetrics.vitals.ratings.${row.rating}`)}</Badge>
                </Td>
              </Tr>
            ))}
          </TBody>
        </ScrollingTable>
      )}
    </Card>
  );
}
