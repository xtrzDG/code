"use client";

/**
 * One customer in a list (the customer list, a segment's members): the
 * name, the VIP / blocked / erased marks, the phone as the viewer may see
 * it, the channels, how many conversations, bookings and requests, the
 * last activity and the first tags. The whole row opens their page.
 */

import Link from "next/link";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChevronRight, IconStar } from "@/components/icons";
import { Badge } from "@/components/ui";
import { CHANNEL_NAMES } from "@/components/workspace/channelNames";
import { useI18n } from "@/i18n/client";
import { listFormat } from "@/lib/intl/formatters";
import { customerPath } from "@/lib/navigation";

import { initialsOf } from "../../inbox/_lib/conversationModel";
import { customerName, shownPhone, type CustomerSummary } from "../_lib/customerModel";

const SHOWN_TAGS = 3;

export function CustomerRow({ contact }: { contact: CustomerSummary }) {
  const { t, tp, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const isErased = Boolean(contact.erased_at);
  const name = isErased ? t("settings.customers.erasedName") : customerName(contact, t("palette.unnamed"));
  const phone = shownPhone(contact);
  const channels = (contact.channels ?? []).map((channel) => t(CHANNEL_NAMES[channel]));
  const tags = contact.tags ?? [];
  const facts = [
    channels.length > 0 ? listFormat(locale, { type: "unit" }).format(channels) : null,
    contact.conversation_count > 0 ? tp("settings.requests.conversations", contact.conversation_count) : null,
    contact.booking_count > 0 ? tp("settings.customers.bookings", contact.booking_count) : null,
    contact.lead_count > 0 ? tp("settings.customers.leads", contact.lead_count) : null,
    isErased && contact.erased_at
      ? t("settings.customers.erasedOn", { date: format.dateTime(contact.erased_at) })
      : t("settings.customers.lastActivity", { date: format.dateTime(contact.last_activity_at) }),
  ].filter(Boolean);

  return (
    <li>
      <Link
        href={customerPath(business.id, contact.id)}
        className="motion-press group flex items-center gap-3 px-4 py-3 hover:bg-surface-muted focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus"
      >
        <span
          aria-hidden
          className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent-ink"
        >
          {isErased ? "–" : initialsOf(contact.name)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span
              dir={contact.name ? "auto" : "ltr"}
              data-user-content={contact.name && !isErased ? true : undefined}
              className={isErased ? "text-sm text-ink-muted" : "text-sm font-medium break-words text-ink"}
            >
              {name}
            </span>
            {contact.is_vip ? (
              <Badge tone="accent" icon={<IconStar className="size-3" aria-hidden />}>
                {t("customers.row.vip")}
              </Badge>
            ) : null}
            {contact.is_blocked ? <Badge tone="warning">{t("customers.row.blocked")}</Badge> : null}
            {isErased ? <Badge tone="neutral">{t("settings.customers.erased")}</Badge> : null}
          </span>
          {phone && contact.name ? (
            <span
              dir="ltr"
              className="mt-0.5 block text-start text-xs text-ink-muted tabular-nums"
              title={phone.isMasked ? t("customers.row.phoneMasked") : undefined}
            >
              {phone.text}
              {phone.isMasked ? <span className="sr-only"> ({t("customers.row.phoneMasked")})</span> : null}
            </span>
          ) : null}
          <span className="mt-0.5 block text-xs text-ink-subtle">{facts.join(" · ")}</span>
          {tags.length > 0 ? (
            <span className="mt-1.5 flex flex-wrap gap-1">
              {tags.slice(0, SHOWN_TAGS).map((tag) => (
                <span key={tag} dir="auto" className="rounded-md bg-surface-muted px-1.5 py-0.5 text-[11px] text-ink-muted">
                  {tag}
                </span>
              ))}
              {tags.length > SHOWN_TAGS ? (
                <span className="px-1 text-[11px] text-ink-subtle">+{tags.length - SHOWN_TAGS}</span>
              ) : null}
            </span>
          ) : null}
        </span>
        <IconChevronRight className="size-4 shrink-0 text-ink-subtle group-hover:text-ink rtl:-scale-x-100" aria-hidden />
      </Link>
    </li>
  );
}
