"use client";

/**
 * Who the customer is at a glance: the standing ("Regular customer · 4
 * visits"), the marks (VIP, blocked, erased), the phone as the viewer may
 * see it, the channels they used, since when they are a customer and
 * their last visit.
 */

import type { ReactNode } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { STANDING_LABELS, standingLine } from "@/components/customers/standing";
import { IconStar } from "@/components/icons";
import { PhoneLink } from "@/components/insights/common";
import { Alert, Badge, Card } from "@/components/ui";
import { CHANNEL_NAMES } from "@/components/workspace/channelNames";
import { useI18n } from "@/i18n/client";
import { listFormat } from "@/lib/intl/formatters";

import { initialsOf } from "../../../inbox/_lib/conversationModel";
import { shownPhone, type CustomerDetail } from "../../_lib/customerModel";

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-subtle">{label}</dt>
      <dd className="mt-0.5 text-sm break-words text-ink">{children}</dd>
    </div>
  );
}

export function CustomerSummaryCard({ detail, name }: { detail: CustomerDetail; name: string }) {
  const i18n = useI18n();
  const { t, locale } = i18n;
  const format = useBusinessFormat();
  const contact = detail.contact;
  const phone = shownPhone(contact);
  const channels = (contact.channels ?? []).map((channel) => t(CHANNEL_NAMES[channel]));
  const standing = detail.standing ?? "new";
  const isErased = Boolean(contact.erased_at);

  return (
    <Card>
      <div className="flex items-start gap-4">
        <span
          aria-hidden
          className="flex size-12 shrink-0 items-center justify-center rounded-full bg-accent-soft text-base font-semibold text-accent-ink"
        >
          {isErased ? "–" : initialsOf(contact.name)}
        </span>
        <div className="min-w-0 flex-1">
          <p dir="auto" className="text-lg font-semibold break-words text-ink">
            {name}
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-accent">{standingLine(i18n, standing, detail.visit_count ?? 0)}</span>
            {contact.is_vip ? (
              <Badge tone="accent" icon={<IconStar className="size-3" aria-hidden />}>
                {t("customers.row.vip")}
              </Badge>
            ) : null}
            {contact.is_blocked ? <Badge tone="warning">{t("customers.row.blocked")}</Badge> : null}
            {isErased ? <Badge tone="neutral">{t("settings.customers.erased")}</Badge> : null}
            {!isErased && contact.is_phone_verified ? <Badge tone="success">{t("settings.customers.verifiedPhone")}</Badge> : null}
            {!isErased && (contact.opted_out_channels ?? []).length > 0 ? (
              <Badge tone="warning">{t("settings.customers.optedOut")}</Badge>
            ) : null}
          </p>
          <span className="sr-only">{t(STANDING_LABELS[standing])}</span>
        </div>
      </div>

      {isErased && contact.erased_at ? (
        <Alert tone="info" className="mt-4">
          {t("customers.detail.erased", { date: format.dateTime(contact.erased_at) })}
        </Alert>
      ) : null}

      <dl className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {phone ? (
          <Fact label={t("customers.detail.phone")}>
            {phone.isMasked ? (
              <span dir="ltr" className="tabular-nums" title={t("customers.row.phoneMasked")}>
                {phone.text}
                <span className="sr-only"> ({t("customers.row.phoneMasked")})</span>
              </span>
            ) : (
              <PhoneLink phone={contact.phone_number ?? ""} />
            )}
          </Fact>
        ) : null}
        {channels.length > 0 ? (
          <Fact label={t("customers.detail.channels")}>{listFormat(locale, { type: "unit" }).format(channels)}</Fact>
        ) : null}
        <Fact label={t("customers.detail.since")}>{format.date(contact.first_seen_at)}</Fact>
        <Fact label={t("customers.detail.lastVisit")}>
          {detail.last_visit_at ? format.date(detail.last_visit_at) : t("customers.detail.noVisits")}
        </Fact>
      </dl>
    </Card>
  );
}
