"use client";

import { useState, type FormEvent } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconExternal } from "@/components/icons";
import { Button, ButtonLink, Field, Select, SkeletonText, UserSentence, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";
import {
  googleChoiceValue,
  linkedGoogleEntry,
  PROBLEM_KEYS,
  sortGoogleCalendars,
  type ResourceCalendarView,
} from "@/lib/resourceCalendar";

import { CalendarSection, SourceStatus } from "./CalendarParts";
import { useGoogleCalendars, type ResourceCalendarState } from "./useResourceCalendar";

/**
 * The one Google calendar whose busy times block the resource: chosen from
 * the business's connected Google account (connected on Channels), with
 * how its last read went, and unlinked in one press.
 */
export function GoogleCalendarSection({ calendar, view }: { calendar: ResourceCalendarState; view: ResourceCalendarView }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const google = view.google;
  const linked = google.calendar_id ?? null;
  const list = useGoogleCalendars(google.is_available && google.is_connected);
  const entries = sortGoogleCalendars(list.data?.items ?? [], locale);
  const [choice, setChoice] = useState("");

  const link = async (event: FormEvent) => {
    event.preventDefault();
    if (!choice) {
      return;
    }
    const result = await calendar.linkGoogle.run(choice);
    if (result.ok) {
      calendar.view.setData(result.data);
      toast.success(t("calendarSync.google.linked"));
      setChoice("");
    }
  };

  const unlink = async () => {
    const result = await calendar.unlinkGoogle.run();
    if (result.ok) {
      toast.success(t("calendarSync.google.unlinked"));
    }
  };

  let body;
  if (!google.is_available) {
    body = <p className="text-sm text-ink-subtle">{t("calendarSync.google.notAvailable")}</p>;
  } else if (!google.is_connected) {
    body = (
      <div className="space-y-3">
        <p className="text-sm text-ink-muted">{t("calendarSync.google.connectFirst")}</p>
        <ButtonLink
          href={businessPath(business.id, "assistant/channels")}
          variant="secondary"
          size="sm"
          leadingIcon={<IconExternal className="size-4" aria-hidden />}
        >
          {t("calendarSync.google.openChannels")}
        </ButtonLink>
      </div>
    );
  } else if (linked) {
    const entry = linkedGoogleEntry(linked, entries);
    body = (
      <div className="space-y-2">
        <p className="text-sm text-ink">
          <UserSentence
            text={
              entry?.is_primary
                ? t("calendarSync.google.current", { name: t("calendarSync.google.primary") })
                : t("calendarSync.google.current")
            }
            values={{ name: entry?.name ?? linked }}
          />
        </p>
        <SourceStatus status={google.status} />
        <Button variant="secondary" size="sm" isLoading={calendar.unlinkGoogle.isPending} onClick={() => void unlink()}>
          {t("calendarSync.google.unlink")}
        </Button>
      </div>
    );
  } else if (list.isLoading && !list.data) {
    body = <SkeletonText lines={2} />;
  } else if (!list.data?.is_readable) {
    const problem = list.data?.problem;
    body = (
      <p className="text-sm text-warning" role="status">
        {problem ? t(PROBLEM_KEYS[problem]) : t("calendarSync.google.listFailed")}
      </p>
    );
  } else {
    body = (
      <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={(event) => void link(event)}>
        <Field label={t("calendarSync.google.calendar")} className="min-w-0 flex-1">
          {(control) => (
            <Select {...control} value={choice} onChange={(event) => setChoice(event.target.value)}>
              <option value="">{t("calendarSync.google.choose")}</option>
              {entries.map((entry) => (
                <option key={entry.calendar_id} value={googleChoiceValue(entry)}>
                  {entry.is_primary ? t("calendarSync.google.primary", { name: entry.name }) : entry.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Button type="submit" size="sm" className="sm:mb-px" disabled={!choice} isLoading={calendar.linkGoogle.isPending}>
          {t("calendarSync.google.link")}
        </Button>
      </form>
    );
  }

  return (
    <CalendarSection title={t("calendarSync.google.title")} description={t("calendarSync.google.description")}>
      {body}
    </CalendarSection>
  );
}
