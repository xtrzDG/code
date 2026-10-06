"use client";

import Link from "next/link";

import type { Schema } from "@/api/types";
import { Badge, Card, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatDate } from "@/lib/format";
import { CANCELLATION_REASON_LABELS, RETENTION_OFFER_LABELS } from "@/lib/subscriptionLifecycle";

import { adminClientPath } from "../../_lib/clients";
import { ScrollingTable } from "./ScrollingTable";
import type { MetricsFormat } from "./useMetricsFormat";

type ChurnView = Schema<"ChurnView">;

/** Whether the period has anything to show. */
export function hasChurnActivity(churn: ChurnView): boolean {
  return (
    churn.cancellations > 0 ||
    (churn.offers ?? []).some((row) => row.accepted > 0) ||
    churn.pauses_scheduled > 0 ||
    churn.pauses_ended > 0 ||
    churn.win_back_sent > 0
  );
}

/**
 * Why owners cancel: the period's cancellations by reason with the offers
 * taken instead, the pauses, the win-back messages and who came back, and
 * the newest owners' own words.
 */
export function ChurnCard({ churn, format }: { churn: ChurnView; format: MetricsFormat }) {
  const { t, locale } = useI18n();
  const title = t("adminChurn.title");
  const reasons = churn.reasons ?? [];
  const offers = (churn.offers ?? []).filter((row) => row.accepted > 0);
  const comments = churn.comments ?? [];
  const saved = (churn.offers ?? []).reduce((total, row) => total + row.accepted, 0);
  const reasonName = (reason: Schema<"CancellationReason"> | null | undefined) =>
    reason ? t(CANCELLATION_REASON_LABELS[reason]) : t("adminChurn.noReason");

  const stats = [
    { label: t("adminChurn.stats.cancellations"), value: churn.cancellations },
    { label: t("adminChurn.stats.saved"), value: saved },
    { label: t("adminChurn.stats.pausesScheduled"), value: churn.pauses_scheduled },
    { label: t("adminChurn.stats.pausesEnded"), value: churn.pauses_ended },
    { label: t("adminChurn.stats.winBackSent"), value: churn.win_back_sent },
    { label: t("adminChurn.stats.returned"), value: churn.returned_after_win_back },
  ];

  return (
    <Card title={title} description={t("adminChurn.description")} padded={false} aria-label={title}>
      {!hasChurnActivity(churn) ? (
        <p className="p-5 text-sm text-ink-muted">{t("adminChurn.empty")}</p>
      ) : (
        <div className="space-y-5 pb-5">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 px-5 pt-5 sm:grid-cols-3 xl:grid-cols-6">
            {stats.map((stat) => (
              <div key={stat.label} className="min-w-0">
                <dt className="text-xs text-ink-muted">{stat.label}</dt>
                <dd className="mt-0.5 text-lg font-semibold text-ink tabular-nums">{format.number(stat.value)}</dd>
              </div>
            ))}
          </dl>

          {reasons.length > 0 ? (
            <ScrollingTable caption={title}>
              <THead>
                <Tr>
                  <Th>{t("adminChurn.reason")}</Th>
                  <Th align="right">{t("adminChurn.cancelled")}</Th>
                  <Th align="right">{t("adminChurn.tookOffer")}</Th>
                </Tr>
              </THead>
              <TBody>
                {reasons.map((row) => (
                  <Tr key={row.reason ?? "none"}>
                    <Th scope="row" className="font-normal text-ink">
                      {reasonName(row.reason)}
                    </Th>
                    <Td align="right" className="tabular-nums">
                      {format.number(row.cancellations)}
                    </Td>
                    <Td align="right" className="tabular-nums">
                      {format.number(row.saved)}
                    </Td>
                  </Tr>
                ))}
              </TBody>
            </ScrollingTable>
          ) : null}

          {offers.length > 0 ? (
            <div className="space-y-2 px-5">
              <h3 className="text-sm font-medium text-ink">{t("adminChurn.offersTitle")}</h3>
              <ul className="flex flex-wrap gap-2">
                {offers.map((row) => (
                  <li key={row.kind}>
                    <Badge tone="accent">
                      {t(RETENTION_OFFER_LABELS[row.kind])} · {format.number(row.accepted)}
                    </Badge>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {comments.length > 0 ? (
            <div className="space-y-2 px-5">
              <h3 className="text-sm font-medium text-ink">{t("adminChurn.commentsTitle")}</h3>
              <ul className="divide-y divide-line rounded-xl border border-line">
                {comments.map((comment) => (
                  <li key={`${comment.business_id}:${comment.occurred_at}`} className="space-y-1 p-3 text-sm">
                    <p className="flex flex-wrap items-center gap-x-2 text-xs text-ink-muted">
                      <span>{reasonName(comment.reason)}</span>
                      <span aria-hidden>·</span>
                      <span>{formatDate(comment.occurred_at, { locale, timeZone: "UTC" })}</span>
                      <span aria-hidden>·</span>
                      <Link href={adminClientPath(comment.business_id)} className="text-accent underline-offset-2 hover:underline">
                        {t("adminChurn.openClient")}
                      </Link>
                    </p>
                    {/* The owner's own words: shown as written. */}
                    <p dir="auto" className="break-words whitespace-pre-line text-ink">
                      {comment.details}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}
    </Card>
  );
}
