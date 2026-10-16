"use client";

import Link from "next/link";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconClock, IconTrash } from "@/components/icons";
import { ChannelBadge } from "@/components/insights/Badges";
import { formatLocalDate, formatLocalTime } from "@/components/insights/dates";
import { usePartyWording } from "@/components/insights/usePartyWording";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { conversationPath } from "@/lib/navigation";

import {
  END_REASON_LABELS,
  isRemovable,
  minutesLeft,
  STATUS_LABELS,
  STATUS_TONES,
  wishedWindow,
  type WaitlistEntry,
} from "../_lib/waitlistModel";
import { useMinuteClock } from "../_lib/useMinuteClock";

const DAY: Intl.DateTimeFormatOptions = { weekday: "short", day: "numeric", month: "short" };

/**
 * One customer on the waitlist: the day, hours and party they wait for,
 * where they wrote from, the place held for them with the minutes left to
 * answer, how the entry ended, and a way to their conversation and off the
 * list.
 */
export function WaitlistEntryCard({ entry, onRemove }: { entry: WaitlistEntry; onRemove: (entry: WaitlistEntry) => void }) {
  const { t, tp, locale } = useI18n();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  const party = usePartyWording({ kind: entry.resource_kind ?? null });
  const name = entry.contact_name ?? t("waitlist.customer");
  const wished = wishedWindow(entry);
  const time = (value: string) => formatLocalTime(value, locale);
  const hours =
    wished.kind === "between"
      ? t("waitlist.window.between", { from: time(wished.from), to: time(wished.to) })
      : wished.kind === "from"
        ? t("waitlist.window.from", { from: time(wished.from) })
        : wished.kind === "until"
          ? t("waitlist.window.until", { to: time(wished.to) })
          : t("waitlist.window.any");
  const wish = [
    t("waitlist.wants", { date: formatLocalDate(entry.date, locale, DAY) }),
    hours,
    party.count(entry.party_size, entry.resource_id),
    entry.nights ? tp("waitlist.nights", entry.nights, { count: entry.nights }) : null,
  ].filter(Boolean);
  const what = [entry.service_title, entry.resource_name].filter(Boolean).join(" · ");

  return (
    <article aria-label={name} className="motion-lift rounded-2xl border border-line bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0 space-y-1">
          <p className="text-base font-semibold text-ink [overflow-wrap:anywhere]">{name}</p>
          <p className="text-sm text-ink">{wish.join(" · ")}</p>
          {what ? <p className="text-sm text-ink-muted">{what}</p> : null}
          {entry.notes ? <p className="text-sm text-ink-muted [overflow-wrap:anywhere]">“{entry.notes}”</p> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={STATUS_TONES[entry.status]}>{t(STATUS_LABELS[entry.status])}</Badge>
          <ChannelBadge channel={entry.source_channel} />
        </div>
      </div>

      {entry.status === "offered" && entry.offer ? <HeldPlace offer={entry.offer} /> : null}
      {entry.status === "expired" && entry.end_reason ? (
        <p className="mt-3 text-sm text-ink-muted">{t(END_REASON_LABELS[entry.end_reason])}</p>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-t border-line pt-3">
        <p className="text-xs text-ink-subtle">
          {entry.status === "booked" && entry.booked_at
            ? t("waitlist.booked", { time: format.dateTime(entry.booked_at) })
            : entry.status === "expired" && entry.ended_at
              ? t("waitlist.ended", { time: format.dateTime(entry.ended_at) })
              : t("waitlist.joined", { time: format.dateTime(entry.created_at) })}
          {entry.offer_count > 0 ? <> · {tp("waitlist.offerCount", entry.offer_count, { count: entry.offer_count })}</> : null}
        </p>
        <div className="flex flex-wrap items-center gap-3">
          {entry.conversation_id ? (
            <Link
              href={conversationPath(business.id, entry.conversation_id)}
              className="text-sm font-medium text-accent underline underline-offset-2 hover:no-underline"
            >
              {t("waitlist.openConversation")}
            </Link>
          ) : null}
          {isRemovable(entry) ? (
            <Button
              variant="danger-ghost"
              size="sm"
              leadingIcon={<IconTrash className="size-4" aria-hidden />}
              onClick={() => onRemove(entry)}
              aria-label={`${t("waitlist.remove")}: ${name}`}
            >
              {t("waitlist.remove")}
            </Button>
          ) : null}
        </div>
      </div>
    </article>
  );
}

/** The place held for the customer, and how long it waits for their answer. */
function HeldPlace({ offer }: { offer: NonNullable<WaitlistEntry["offer"]> }) {
  const { t, tp, locale } = useI18n();
  const format = useBusinessFormat();
  const now = useMinuteClock(offer.expires_at !== null && offer.expires_at !== undefined);
  const left = minutesLeft(offer.expires_at, now);
  const hours = [offer.time, offer.end_time].filter((value): value is string => Boolean(value)).map((value) => formatLocalTime(value, locale));
  const when = [formatLocalDate(offer.date, locale, DAY), hours.join("–")].filter(Boolean).join(", ");
  return (
    <div className="mt-3 rounded-xl border border-accent/25 bg-accent-soft px-3 py-2.5 text-sm">
      <p className="font-medium text-ink">
        {offer.resource_name ? t("waitlist.offer.held", { place: offer.resource_name, time: when }) : t("waitlist.offer.heldNoPlace", { time: when })}
      </p>
      <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-ink-muted">
        <IconClock className="size-4 text-accent" aria-hidden />
        {offer.expires_at ? (
          <>
            <span>{t("waitlist.offer.until", { time: format.time(offer.expires_at) })}</span>
            {left !== null && left > 0 ? (
              <span className="font-medium text-accent-ink tabular-nums">{tp("waitlist.offer.minutesLeft", left, { count: left })}</span>
            ) : null}
          </>
        ) : (
          <span>{t("waitlist.offer.answerDue")}</span>
        )}
      </p>
    </div>
  );
}
