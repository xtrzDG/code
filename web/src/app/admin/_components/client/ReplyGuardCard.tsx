"use client";

import { Alert, Card } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";

import type { AdminClientSummary } from "../../_lib/clients";
import { guardFigures, isHeldBackOften, isProbed } from "../../_lib/replyGuard";

/**
 * What the reply guard did for the client in the last 7 days: replies it
 * held back (rewritten once or passed to staff) and messages that tried to
 * change the assistant's instructions
 * (GET /v1/admin/clients/{business_id}, `summary.guard_activity`).
 */
export function ReplyGuardCard({ summary }: { summary: AdminClientSummary }) {
  const { t, locale } = useI18n();
  const figures = guardFigures(summary.guard_activity);
  const heldBackOften = isHeldBackOften(figures);
  const probed = isProbed(figures);
  const number = (value: number) => <span className="tabular-nums">{formatNumber(value, locale)}</span>;

  return (
    <Card title={t("adminReplyGuard.title")} description={t("adminReplyGuard.description")}>
      {figures.checked === 0 && figures.injectionFlags === 0 ? (
        <p className="text-sm text-ink-muted">{t("adminReplyGuard.empty")}</p>
      ) : (
        <div className="space-y-5">
          <Facts
            columns={3}
            items={[
              { label: t("adminReplyGuard.checked"), value: number(figures.checked) },
              {
                label: t("adminReplyGuard.heldBack"),
                value: (
                  <span className={cn("tabular-nums", heldBackOften && "text-danger")}>
                    {formatNumber(figures.heldBack, locale)}
                    {figures.heldBackShare !== null ? (
                      <span className="ms-2 text-sm text-ink-muted">
                        {t("adminReplyGuard.heldBackShare", {
                          share: formatNumber(figures.heldBackShare, locale, {
                            style: "percent",
                            maximumFractionDigits: 0,
                          }),
                        })}
                      </span>
                    ) : null}
                  </span>
                ),
              },
              { label: t("adminReplyGuard.rewritten"), value: number(figures.rewritten) },
              { label: t("adminReplyGuard.handedOff"), value: number(figures.handedOff) },
              {
                label: t("adminReplyGuard.injectionFlags"),
                value: (
                  <span className={cn("tabular-nums", probed && "text-danger")}>
                    {formatNumber(figures.injectionFlags, locale)}
                  </span>
                ),
              },
            ]}
          />
          {heldBackOften ? <Alert tone="warning">{t("adminReplyGuard.heldBackNote")}</Alert> : null}
          {probed ? <Alert tone="warning">{t("adminReplyGuard.probedNote")}</Alert> : null}
        </div>
      )}
    </Card>
  );
}
