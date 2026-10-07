"use client";

import { useState, type FormEvent } from "react";

import { IconTrash } from "@/components/icons";
import { Button, Field, Input, UserContent, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { feedAddressError, type ResourceCalendarView } from "@/lib/resourceCalendar";

import { CalendarSection, SourceStatus } from "./CalendarParts";
import type { ResourceCalendarState } from "./useResourceCalendar";

/** A resource imports at most this many calendars (the API refuses more). */
const FEED_LIMIT = 5;

/**
 * Calendars imported by address (Airbnb, Booking.com, Vrbo, any iCal
 * feed): each by its site only (the address stays private), how its last
 * read went, and removed in one press; a form adds one more.
 */
export function IcalImportSection({ calendar, view }: { calendar: ResourceCalendarState; view: ResourceCalendarView }) {
  const { t } = useI18n();
  const toast = useToast();
  const [address, setAddress] = useState("");
  const [error, setError] = useState<MessageKey | null>(null);
  const feeds = view.ical_imports;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const problem = feedAddressError(address);
    setError(problem);
    if (problem) {
      return;
    }
    const result = await calendar.importFeed.run(address.trim());
    if (result.ok) {
      calendar.view.setData(result.data);
      toast.success(t("calendarSync.ical.imported"));
      setAddress("");
    }
  };

  const remove = async (feedId: string) => {
    const result = await calendar.removeFeed.run(feedId);
    if (result.ok) {
      toast.success(t("calendarSync.ical.removed"));
    }
  };

  return (
    <CalendarSection title={t("calendarSync.ical.title")} description={t("calendarSync.ical.description")}>
      {feeds.length === 0 ? (
        <p className="text-sm text-ink-subtle">{t("calendarSync.ical.empty")}</p>
      ) : (
        <ul className="divide-y divide-line rounded-xl border border-line">
          {feeds.map((feed) => (
            <li key={feed.feed_id} className="flex items-start gap-3 px-3 py-2.5">
              <div className="min-w-0 flex-1 space-y-0.5">
                <p className="truncate text-sm font-medium text-ink">
                  <UserContent dir="ltr">{feed.host}</UserContent>
                </p>
                <SourceStatus status={feed.status} />
              </div>
              <Button
                variant="ghost"
                size="sm"
                leadingIcon={<IconTrash className="size-4" aria-hidden />}
                aria-label={t("calendarSync.ical.removeLabel", { host: feed.host })}
                disabled={calendar.removeFeed.isPending}
                onClick={() => void remove(feed.feed_id)}
              >
                <span className="hidden sm:inline">{t("calendarSync.ical.remove")}</span>
              </Button>
            </li>
          ))}
        </ul>
      )}
      {feeds.length >= FEED_LIMIT ? (
        <p className="text-sm text-ink-subtle">{t("calendarSync.ical.limit")}</p>
      ) : (
        <form className="space-y-3" noValidate onSubmit={(event) => void submit(event)}>
          <Field label={t("calendarSync.ical.address")} hint={t("calendarSync.ical.addressHint")} error={error ? t(error) : undefined}>
            {(control) => (
              <Input
                {...control}
                type="url"
                inputMode="url"
                autoComplete="off"
                spellCheck={false}
                dir="ltr"
                value={address}
                onChange={(event) => {
                  setAddress(event.target.value);
                  setError(null);
                }}
              />
            )}
          </Field>
          <Button type="submit" size="sm" variant="secondary" isLoading={calendar.importFeed.isPending}>
            {t("calendarSync.ical.import")}
          </Button>
        </form>
      )}
    </CalendarSection>
  );
}
