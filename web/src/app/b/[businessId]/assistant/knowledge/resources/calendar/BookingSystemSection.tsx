"use client";

import { useState, type FormEvent } from "react";

import { Button, Field, Input, Select, UserSentence, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { bookingSystemErrors, type ResourceCalendarView } from "@/lib/resourceCalendar";
import type { Schema } from "@/api/types";

import { CalendarSection, SourceStatus } from "./CalendarParts";
import type { ResourceCalendarState } from "./useResourceCalendar";

type BookingSystemKind = Schema<"BookingSystemKind">;

/** The names of the booking systems the platform can follow. */
const SYSTEM_NAMES: Readonly<Record<BookingSystemKind, MessageKey>> = {
  cal_com: "calendarSync.integrations.kinds.cal_com",
};

/**
 * A booking system whose bookings block the resource (Cal.com first): the
 * event type it follows there and the business's API key, which is sealed
 * and never shown again; disconnected in one press.
 */
export function BookingSystemSection({ calendar, view }: { calendar: ResourceCalendarState; view: ResourceCalendarView }) {
  const { t } = useI18n();
  const toast = useToast();
  const kinds = view.booking_system_kinds;
  const [kind, setKind] = useState<BookingSystemKind | "">(kinds[0] ?? "");
  const [eventType, setEventType] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [errors, setErrors] = useState<{ eventType?: MessageKey; apiKey?: MessageKey }>({});
  const linked = view.booking_system;

  if (kinds.length === 0 && !linked) {
    return null;
  }

  const connect = async (event: FormEvent) => {
    event.preventDefault();
    const found = bookingSystemErrors(eventType, apiKey);
    setErrors(found);
    if (found.eventType || found.apiKey || !kind) {
      return;
    }
    const result = await calendar.linkBookingSystem.run({ kind, external_resource_id: eventType.trim(), api_key: apiKey.trim() });
    if (result.ok) {
      calendar.view.setData(result.data);
      toast.success(t("calendarSync.bookingSystem.connected"));
      setEventType("");
      setApiKey("");
    }
  };

  const disconnect = async () => {
    const result = await calendar.unlinkBookingSystem.run();
    if (result.ok) {
      toast.success(t("calendarSync.bookingSystem.disconnected"));
    }
  };

  return (
    <CalendarSection title={t("calendarSync.bookingSystem.title")} description={t("calendarSync.bookingSystem.description")}>
      {linked ? (
        <div className="space-y-2">
          <p className="text-sm text-ink">
            <span className="font-medium">{t(SYSTEM_NAMES[linked.kind])}</span>
            {" · "}
            <UserSentence
              text={t("calendarSync.bookingSystem.following")}
              values={{ title: linked.external_resource_title ?? linked.external_resource_id }}
            />
          </p>
          <SourceStatus status={linked.status} />
          <Button variant="secondary" size="sm" isLoading={calendar.unlinkBookingSystem.isPending} onClick={() => void disconnect()}>
            {t("calendarSync.bookingSystem.disconnect")}
          </Button>
        </div>
      ) : (
        <form className="space-y-3" noValidate onSubmit={(event) => void connect(event)}>
          {kinds.length > 1 ? (
            <Field label={t("calendarSync.bookingSystem.system")}>
              {(control) => (
                <Select {...control} value={kind} onChange={(event) => setKind(event.target.value as BookingSystemKind)}>
                  {kinds.map((option) => (
                    <option key={option} value={option}>
                      {t(SYSTEM_NAMES[option])}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <Field
              label={t("calendarSync.bookingSystem.eventType")}
              hint={t("calendarSync.bookingSystem.eventTypeHint")}
              error={errors.eventType ? t(errors.eventType) : undefined}
              required
            >
              {(control) => (
                <Input
                  {...control}
                  inputMode="numeric"
                  autoComplete="off"
                  dir="ltr"
                  value={eventType}
                  onChange={(event) => {
                    setEventType(event.target.value);
                    setErrors((current) => ({ ...current, eventType: undefined }));
                  }}
                />
              )}
            </Field>
            <Field
              label={t("calendarSync.bookingSystem.apiKey")}
              hint={t("calendarSync.bookingSystem.apiKeyHint")}
              error={errors.apiKey ? t(errors.apiKey) : undefined}
              required
            >
              {(control) => (
                <Input
                  {...control}
                  type="password"
                  autoComplete="off"
                  spellCheck={false}
                  dir="ltr"
                  value={apiKey}
                  onChange={(event) => {
                    setApiKey(event.target.value);
                    setErrors((current) => ({ ...current, apiKey: undefined }));
                  }}
                />
              )}
            </Field>
          </div>
          <Button type="submit" size="sm" variant="secondary" isLoading={calendar.linkBookingSystem.isPending}>
            {t("calendarSync.bookingSystem.connect")}
          </Button>
        </form>
      )}
    </CalendarSection>
  );
}
