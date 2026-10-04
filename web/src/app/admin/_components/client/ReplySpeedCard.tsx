"use client";

import { CHANNEL_LABELS } from "@/components/insights/labels";
import { Alert, Card, Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import type { AdminClientSummary } from "../../_lib/clients";
import { channelRows, formatWait, isSlowPercentile } from "../../_lib/replySpeed";

/**
 * How long the client's customers waited for the assistant in the last 7
 * days: the median and the 95th percentile over every channel and per
 * channel (GET /v1/admin/clients/{business_id}, `summary.reply_speed`).
 */
export function ReplySpeedCard({ summary }: { summary: AdminClientSummary }) {
  const { t, locale } = useI18n();
  const speed = summary.reply_speed;
  const rows = channelRows(speed);

  const wait = (milliseconds: number | null | undefined) => {
    if (milliseconds === null || milliseconds === undefined) {
      return "—";
    }
    const { value, unit } = formatWait(milliseconds, locale);
    return t(unit === "minutes" ? "adminReplySpeed.minutes" : "adminReplySpeed.seconds", { value });
  };

  return (
    <Card title={t("adminReplySpeed.title")} description={t("adminReplySpeed.description")}>
      {!speed || speed.reply_count === 0 ? (
        <p className="text-sm text-ink-muted">{t("adminReplySpeed.empty")}</p>
      ) : (
        <div className="space-y-5">
          <Facts
            columns={3}
            items={[
              { label: t("adminReplySpeed.median"), value: <span className="tabular-nums">{wait(speed.p50_ms)}</span> },
              {
                label: t("adminReplySpeed.p95"),
                value: (
                  <span className={isSlowPercentile(speed.p95_ms) ? "text-danger tabular-nums" : "tabular-nums"}>
                    {wait(speed.p95_ms)}
                  </span>
                ),
              },
              { label: t("adminReplySpeed.replies"), value: <span className="tabular-nums">{formatNumber(speed.reply_count, locale)}</span> },
            ]}
          />
          {isSlowPercentile(speed.p95_ms) ? <Alert tone="warning">{t("adminReplySpeed.slowNote")}</Alert> : null}
          {rows.length > 0 ? (
            <div className="overflow-x-auto rounded-xl border border-line">
              <Table caption={t("adminReplySpeed.tableCaption")}>
                <THead>
                  <Tr>
                    <Th>{t("adminReplySpeed.channel")}</Th>
                    <Th align="right">{t("adminReplySpeed.channelReplies")}</Th>
                    <Th align="right">{t("adminReplySpeed.channelMedian")}</Th>
                    <Th align="right">{t("adminReplySpeed.channelP95")}</Th>
                  </Tr>
                </THead>
                <TBody>
                  {rows.map((row) => (
                    <Tr key={row.channel}>
                      <Td>{t(CHANNEL_LABELS[row.channel])}</Td>
                      <Td align="right" className="tabular-nums">
                        {formatNumber(row.reply_count, locale)}
                      </Td>
                      <Td align="right" className="tabular-nums">
                        {wait(row.p50_ms)}
                      </Td>
                      <Td align="right" className={isSlowPercentile(row.p95_ms) ? "text-danger tabular-nums" : "tabular-nums"}>
                        {wait(row.p95_ms)}
                      </Td>
                    </Tr>
                  ))}
                </TBody>
              </Table>
            </div>
          ) : null}
        </div>
      )}
    </Card>
  );
}
