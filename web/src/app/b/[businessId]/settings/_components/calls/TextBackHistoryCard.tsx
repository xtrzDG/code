"use client";

import Link from "next/link";

import type { Query } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconPhone } from "@/components/icons";
import { Badge, Card, EmptyState, ErrorState, SkeletonRows } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { conversationPath } from "@/lib/navigation";

import {
  MISSED_CALL_REASON_LABELS,
  SKIP_REASON_LABELS,
  TEXT_BACK_CHANNEL_LABELS,
  TEXT_BACK_STATUS_LABELS,
  TEXT_BACK_STATUS_TONES,
  type TextBackPage,
  type TextBackView,
} from "../../_lib/calls";

/** The latest callers who did not get through, and what became of their message. */
export function TextBackHistoryCard({ textBacks }: { textBacks: Query<TextBackPage> }) {
  const { t } = useI18n();
  const items = textBacks.data?.items ?? [];
  return (
    <Card
      title={t("callSettings.history.title")}
      description={t("callSettings.history.description")}
      padded={items.length === 0}
    >
      {textBacks.error && !textBacks.data ? (
        <ErrorState error={textBacks.error} onRetry={textBacks.reload} className="py-6" />
      ) : !textBacks.data ? (
        <SkeletonRows rows={3} />
      ) : items.length === 0 ? (
        <EmptyState
          className="py-6"
          icon={<IconPhone className="size-6" />}
          title={t("callSettings.history.empty")}
          description={t("callSettings.history.emptyDescription")}
        />
      ) : (
        <ul className="divide-y divide-line">
          {items.map((item) => (
            <TextBackRow key={item.id} item={item} />
          ))}
        </ul>
      )}
    </Card>
  );
}

function TextBackRow({ item }: { item: TextBackView }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  return (
    <li className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-start sm:justify-between sm:px-6">
      <div className="min-w-0 space-y-0.5">
        <p className="text-sm font-medium text-ink">
          {item.caller_phone_number ? (
            <span dir="ltr" className="tabular-nums">
              {item.caller_phone_number}
            </span>
          ) : (
            t("callSettings.history.hiddenNumber")
          )}
        </p>
        <p className="text-sm text-ink-muted">
          {format.dateTime(item.called_at)} · {t(MISSED_CALL_REASON_LABELS[item.reason])}
        </p>
        {item.status === "skipped" && item.skip_reason ? (
          <p className="text-sm text-ink-muted">
            {t("callSettings.history.notSentBecause", { reason: t(SKIP_REASON_LABELS[item.skip_reason]) })}
          </p>
        ) : null}
        {item.status === "failed" && item.last_error ? (
          <p className="text-sm text-danger [overflow-wrap:anywhere]">{item.last_error}</p>
        ) : null}
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
        <Badge tone={TEXT_BACK_STATUS_TONES[item.status]}>{t(TEXT_BACK_STATUS_LABELS[item.status])}</Badge>
        {item.channel && item.status !== "skipped" ? (
          <Badge tone="neutral">{t(TEXT_BACK_CHANNEL_LABELS[item.channel])}</Badge>
        ) : null}
        {item.conversation_id ? (
          <Link
            href={conversationPath(business.id, item.conversation_id)}
            className="text-sm font-medium text-accent underline underline-offset-2 hover:no-underline"
          >
            {t("callSettings.history.openConversation")}
          </Link>
        ) : null}
      </div>
    </li>
  );
}
