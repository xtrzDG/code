"use client";

import Link from "next/link";

import type { Query } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconStar } from "@/components/icons";
import { ChannelBadge } from "@/components/insights/Badges";
import { Badge, Card, EmptyState, ErrorState, SkeletonRows, UserContent } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { conversationPath } from "@/lib/navigation";

import {
  REQUEST_STATUS_LABELS,
  REQUEST_STATUS_TONES,
  SKIP_REASON_LABELS,
  type FeedbackRequestPage,
  type FeedbackRequestView,
} from "../../_lib/reviews";

/** The latest visits asked about: the customer, what became of the request, their rating. */
export function FeedbackRequestsCard({ requests }: { requests: Query<FeedbackRequestPage> }) {
  const { t } = useI18n();
  const items = requests.data?.items ?? [];
  return (
    <Card
      title={t("reviewSettings.requests.title")}
      description={t("reviewSettings.requests.description")}
      padded={items.length === 0}
    >
      {requests.error && !requests.data ? (
        <ErrorState error={requests.error} onRetry={requests.reload} className="py-6" />
      ) : !requests.data ? (
        <SkeletonRows rows={3} />
      ) : items.length === 0 ? (
        <EmptyState
          className="py-6"
          icon={<IconStar className="size-6" />}
          title={t("reviewSettings.requests.empty")}
          description={t("reviewSettings.requests.emptyDescription")}
        />
      ) : (
        <ul className="divide-y divide-line">
          {items.map((item) => (
            <RequestRow key={item.id} item={item} />
          ))}
        </ul>
      )}
    </Card>
  );
}

function RequestRow({ item }: { item: FeedbackRequestView }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  return (
    <li className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-start sm:justify-between sm:px-6">
      <div className="min-w-0 space-y-0.5">
        <p className="text-sm font-medium text-ink [overflow-wrap:anywhere]">
          {item.contact_name ? <UserContent>{item.contact_name}</UserContent> : t("reviewSettings.requests.customer")}
        </p>
        <p className="text-sm text-ink-muted">
          {t("reviewSettings.requests.visitEnded", { time: format.dateTime(item.visit_ended_at) })}
        </p>
        {item.score != null ? (
          <p className="inline-flex items-center gap-1.5 text-sm text-ink">
            <IconStar className="size-4 fill-current text-warning" aria-hidden />
            {t("reviewSettings.requests.rating", { score: item.score })}
          </p>
        ) : null}
        {item.status === "skipped" && item.skip_reason ? (
          <p className="text-sm text-ink-muted">
            {t("reviewSettings.requests.notAskedBecause", { reason: t(SKIP_REASON_LABELS[item.skip_reason]) })}
          </p>
        ) : null}
        {item.status === "failed" && item.last_error ? (
          <p className="text-sm text-danger [overflow-wrap:anywhere]">{item.last_error}</p>
        ) : null}
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
        <Badge tone={REQUEST_STATUS_TONES[item.status]}>{t(REQUEST_STATUS_LABELS[item.status])}</Badge>
        {item.channel && item.status !== "skipped" ? <ChannelBadge channel={item.channel} /> : null}
        {item.review_clicks > 0 ? <Badge tone="accent">{t("reviewSettings.requests.openedLink")}</Badge> : null}
        {item.conversation_id ? (
          <Link
            href={conversationPath(business.id, item.conversation_id)}
            className="text-sm font-medium text-accent underline underline-offset-2 hover:no-underline"
          >
            {t("reviewSettings.requests.openConversation")}
          </Link>
        ) : null}
      </div>
    </li>
  );
}
