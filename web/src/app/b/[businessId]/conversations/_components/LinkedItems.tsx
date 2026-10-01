"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { BookingStatusBadge, HandoffStatusBadge, HandoffUrgencyBadge, LeadStatusBadge } from "@/components/insights/Badges";
import { addDays, formatLocalDate, formatLocalTime, todayIn } from "@/components/insights/dates";
import { HANDOFF_REASONS, LEAD_TYPES } from "@/components/insights/labels";
import type { ConversationSummaryView } from "@/components/insights/types";
import { Card, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

/** Recent and upcoming bookings of the contact are shown from this many days back. */
const BOOKINGS_LOOKBACK_DAYS = 30;

/**
 * What came out of the conversation: its handoffs and leads (matched by
 * conversation) and the customer's recent and upcoming bookings (the API
 * does not link bookings to conversations, so they are matched by contact).
 */
export function LinkedItems({ conversation }: { conversation: ConversationSummaryView }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const [today] = useState(() => todayIn(business.timezone));
  const businessId = business.id;
  const includeSandbox = conversation.is_sandbox ? "true" : undefined;

  const handoffs = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/handoffs", {
        params: { path: { business_id: businessId }, query: { include_sandbox: includeSandbox } },
      }),
    [businessId, includeSandbox],
  );
  const leads = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/leads", {
        params: { path: { business_id: businessId }, query: { include_sandbox: includeSandbox } },
      }),
    [businessId, includeSandbox],
  );
  const bookings = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/bookings", {
        params: {
          path: { business_id: businessId },
          query: { from: addDays(today, -BOOKINGS_LOOKBACK_DAYS), include_sandbox: includeSandbox },
        },
      }),
    [businessId, includeSandbox, today],
  );

  const linkedHandoffs = (handoffs.data?.items ?? []).filter((item) => item.conversation_id === conversation.id);
  const linkedLeads = (leads.data?.items ?? []).filter((item) => item.conversation_id === conversation.id);
  const contactBookings = (bookings.data?.items ?? []).filter((item) => item.contact_id === conversation.contact_id);
  const isLoading = !handoffs.data || !leads.data || !bookings.data;
  const isEmpty = linkedHandoffs.length + linkedLeads.length + contactBookings.length === 0;

  if (!isLoading && isEmpty) {
    return null;
  }

  return (
    <Card title={t("conversations.linked.title")}>
      {isLoading && isEmpty ? (
        <Spinner size="sm" label={t("common.loading")} className="text-ink-subtle" />
      ) : (
        <div className="space-y-4">
          {linkedHandoffs.length > 0 ? (
            <LinkedGroup title={t("conversations.linked.handoffs")} href={businessPath(businessId, "handoffs")}>
              {linkedHandoffs.map((handoff) => (
                <li key={handoff.id} className="flex flex-wrap items-center gap-2">
                  <span className="text-ink">{t(HANDOFF_REASONS[handoff.reason])}</span>
                  <HandoffUrgencyBadge urgency={handoff.urgency} />
                  <HandoffStatusBadge status={handoff.status} />
                </li>
              ))}
            </LinkedGroup>
          ) : null}
          {linkedLeads.length > 0 ? (
            <LinkedGroup title={t("conversations.linked.leads")} href={businessPath(businessId, "leads")}>
              {linkedLeads.map((lead) => (
                <li key={lead.id} className="flex flex-wrap items-center gap-2">
                  <span className="text-ink">{t(LEAD_TYPES[lead.lead_type])}</span>
                  {lead.requested_date ? (
                    <span className="text-ink-muted">{formatLocalDate(lead.requested_date, locale)}</span>
                  ) : null}
                  <LeadStatusBadge status={lead.status} />
                </li>
              ))}
            </LinkedGroup>
          ) : null}
          {contactBookings.length > 0 ? (
            <LinkedGroup title={t("conversations.linked.bookings")} href={businessPath(businessId, "bookings")}>
              {contactBookings.map((booking) => (
                <li key={booking.id} className="flex flex-wrap items-center gap-2">
                  <span className="text-ink">
                    {formatLocalDate(booking.date, locale, { weekday: "short", day: "numeric", month: "short" })}
                    {booking.time ? `, ${formatLocalTime(booking.time, locale)}` : ""}
                  </span>
                  <span dir="auto" className="text-ink-muted">
                    {booking.resource_name}
                  </span>
                  <BookingStatusBadge status={booking.status} />
                </li>
              ))}
            </LinkedGroup>
          ) : null}
        </div>
      )}
    </Card>
  );
}

function LinkedGroup({ title, href, children }: { title: string; href: string; children: ReactNode }) {
  const { t } = useI18n();
  return (
    <section>
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-ink-muted">{title}</h3>
        <Link href={href} className="text-sm font-medium text-accent hover:underline">
          {t("conversations.linked.open")}
          <span className="sr-only"> {title}</span>
        </Link>
      </div>
      <ul className="space-y-1.5 text-sm">{children}</ul>
    </section>
  );
}
