"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlus } from "@/components/icons";
import { BookingStatusBadge, HandoffStatusBadge, HandoffUrgencyBadge, LeadStatusBadge } from "@/components/insights/Badges";
import { formatLocalDate, formatLocalTime } from "@/components/insights/dates";
import { HANDOFF_REASONS, LEAD_TYPES } from "@/components/insights/labels";
import type { ConversationDetailView } from "@/components/insights/types";
import { Button, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

/**
 * What came out of the conversation: the bookings, leads and handoffs made
 * in it (by the assistant's tools or by staff from this card), and a button
 * to book for this customer.
 */
export function LinkedItems({
  detail,
  onBook,
}: {
  detail: ConversationDetailView;
  /** Null hides the booking button (test conversations). */
  onBook: (() => void) | null;
}) {
  const { t, tp, locale } = useI18n();
  const { business } = useBusiness();
  const businessId = business.id;
  const handoffs = detail.handoffs ?? [];
  const leads = detail.leads ?? [];
  const bookings = detail.bookings ?? [];
  const isEmpty = handoffs.length + leads.length + bookings.length === 0;

  const bookButton = onBook ? (
    <Button variant="secondary" size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={onBook}>
      {t("conversations.linked.book")}
    </Button>
  ) : undefined;

  if (isEmpty && !onBook) {
    return null;
  }

  return (
    <Card title={t("conversations.linked.title")} actions={bookButton}>
      {isEmpty ? (
        <p className="text-sm text-ink-muted">{t("conversations.linked.empty")}</p>
      ) : (
        <div className="space-y-4">
          {handoffs.length > 0 ? (
            <LinkedGroup title={t("conversations.linked.handoffs")} href={businessPath(businessId, "handoffs")}>
              {handoffs.map((handoff) => (
                <li key={handoff.id} className="flex flex-wrap items-center gap-2">
                  <span className="text-ink">{t(HANDOFF_REASONS[handoff.reason])}</span>
                  <HandoffUrgencyBadge urgency={handoff.urgency} />
                  <HandoffStatusBadge status={handoff.status} />
                </li>
              ))}
            </LinkedGroup>
          ) : null}
          {leads.length > 0 ? (
            <LinkedGroup title={t("conversations.linked.leads")} href={businessPath(businessId, "leads")}>
              {leads.map((lead) => (
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
          {bookings.length > 0 ? (
            <LinkedGroup title={t("conversations.linked.bookings")} href={businessPath(businessId, "bookings")}>
              {bookings.map((booking) => (
                <li key={booking.id} className="flex flex-wrap items-center gap-2">
                  <span className="text-ink">
                    {formatLocalDate(booking.date, locale, { weekday: "short", day: "numeric", month: "short" })}
                    {booking.time ? `, ${formatLocalTime(booking.time, locale)}` : ""}
                  </span>
                  <span dir="auto" className="text-ink-muted">
                    {booking.resource_name}
                  </span>
                  <span className="text-ink-muted">{tp("bookings.guests", booking.party_size)}</span>
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
