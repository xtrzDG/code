"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCalendar, IconHandoff, IconInbox, IconUsers } from "@/components/icons";
import { useToday } from "@/components/insights/useToday";
import { useAttentionCounts } from "@/components/shell/LiveEvents";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { AttentionTile } from "./DashboardWidgets";

/**
 * A staff member's day at a glance: conversations assigned to them, the
 * customers waiting for a person, new requests and today's bookings (how
 * many are still to come and to confirm), each opening where it is
 * handled. Counts only: nothing here is an audited view of customer data.
 */
export function TodayQueue() {
  const { t } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const today = useToday(business.timezone);
  const counts = useAttentionCounts();
  const path = { business_id: business.id };
  const views = useQuery(queryKeys.dashboard.inboxViews(business.id), () =>
    api.GET("/v1/businesses/{business_id}/inbox/counts", { params: { path } }),
  );
  const queue = useQuery(queryKeys.dashboard.todayQueue(business.id, today), () =>
    api.GET("/v1/businesses/{business_id}/today-queue", { params: { path } }),
  );
  const bookings = queue.data;

  return (
    <section aria-labelledby="dashboard-queue" className="space-y-3">
      <h2 id="dashboard-queue" className="text-sm font-semibold tracking-wide text-ink-muted uppercase">
        {t("value.queue.title")}
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <AttentionTile
          href={businessPath(business.id, "messages")}
          label={t("value.queue.mine")}
          hint={t("value.queue.mineHint")}
          count={views.data?.mine}
          formatCount={format.number}
          actionLabel={t("dashboard.attention.open")}
          icon={<IconUsers className="size-5" />}
        />
        <AttentionTile
          href={businessPath(business.id, "messages/handoffs")}
          label={t("dashboard.attention.openHandoffs")}
          hint={t("dashboard.attention.openHandoffsHint")}
          count={counts?.openHandoffs}
          formatCount={format.number}
          actionLabel={t("dashboard.attention.open")}
          icon={<IconHandoff className="size-5" />}
        />
        <AttentionTile
          href={businessPath(business.id, "messages/leads")}
          label={t("value.queue.requests")}
          hint={t("value.queue.requestsHint")}
          count={counts?.newLeads}
          formatCount={format.number}
          actionLabel={t("dashboard.attention.open")}
          icon={<IconInbox className="size-5" />}
        />
        <AttentionTile
          href={`${businessPath(business.id, "bookings")}?range=today`}
          label={t("value.queue.bookings")}
          hint={
            bookings
              ? t("value.queue.bookingsHint", {
                  upcoming: format.number(bookings.upcoming_booking_count),
                  unconfirmed: format.number(bookings.unconfirmed_booking_count),
                })
              : t("value.queue.bookingsLoading")
          }
          count={bookings?.booking_count}
          formatCount={format.number}
          actionLabel={t("dashboard.attention.open")}
          icon={<IconCalendar className="size-5" />}
        />
      </div>
    </section>
  );
}
