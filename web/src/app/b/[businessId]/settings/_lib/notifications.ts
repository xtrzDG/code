/**
 * Pure helpers of Settings → Notifications: events and quiet hours (of a
 * staff contact or of my own devices), delivery states, check results and
 * which device in the list is this browser.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";
import type { MessageKey } from "@/i18n/translate";
import type { RememberedDevice } from "@/lib/webPush";

export type StaffAlertEvent = Schema<"StaffAlertEvent">;
export type NotificationPreferences = Schema<"StaffNotificationPreferences">;
export type StaffDelivery = Schema<"StaffDeliveryView">;
export type DeliveryStatus = Schema<"OutboundMessageStatus">;
export type NotificationContact = Schema<"NotificationContactView">;
export type MyNotificationSettings = Schema<"MyNotificationSettingsView">;
export type PushDevice = Schema<"PushDeviceView">;
export type NotificationCheckResult = Schema<"NotificationCheckResult">;

export const ALL_EVENTS: readonly StaffAlertEvent[] = ["handoff", "lead", "booking"];

export const EVENT_LABELS: Record<StaffAlertEvent, MessageKey> = {
  handoff: "notifications.preferences.event.handoff",
  lead: "notifications.preferences.event.lead",
  booking: "notifications.preferences.event.booking",
};

const EVENT_SHORT_LABELS: Record<StaffAlertEvent, MessageKey> = {
  handoff: "notifications.preferences.short.handoff",
  lead: "notifications.preferences.short.lead",
  booking: "notifications.preferences.short.booking",
};

export const DELIVERY_TONES: Record<DeliveryStatus, BadgeTone> = {
  delivered: "success",
  pending: "warning",
  dead: "danger",
};

export const DELIVERY_LABELS: Record<DeliveryStatus, MessageKey> = {
  delivered: "notifications.contacts.status.delivered",
  pending: "notifications.contacts.status.pending",
  dead: "notifications.contacts.status.dead",
};

/** Quiet hours a person starts from when they turn them on. */
export const DEFAULT_QUIET_HOURS = { from: "22:00", until: "08:00" } as const;

/** Events and quiet hours as a form edits them (the hours kept while switched off). */
export interface PreferencesForm {
  events: StaffAlertEvent[];
  hasQuietHours: boolean;
  from: string;
  until: string;
}

export type QuietHoursError = "format" | "same";

const TIME_OF_DAY = /^([01]\d|2[0-3]):[0-5]\d$/;

/** No stored choice means every event at any hour. */
export function preferencesForm(preferences: NotificationPreferences | null | undefined): PreferencesForm {
  const quiet = preferences?.quiet_hours ?? null;
  return {
    events: ALL_EVENTS.filter((event) => (preferences?.events ?? ALL_EVENTS).includes(event)),
    hasQuietHours: quiet !== null,
    from: quiet?.starts_at ?? DEFAULT_QUIET_HOURS.from,
    until: quiet?.ends_at ?? DEFAULT_QUIET_HOURS.until,
  };
}

/** The events with one switched on or off, in their usual order. */
export function toggleEvent(events: readonly StaffAlertEvent[], event: StaffAlertEvent, on: boolean): StaffAlertEvent[] {
  return ALL_EVENTS.filter((candidate) => (candidate === event ? on : events.includes(candidate)));
}

/** What is wrong with the quiet hours (only checked while they are on). */
export function quietHoursErrors(form: PreferencesForm): { from?: QuietHoursError; until?: QuietHoursError } {
  if (!form.hasQuietHours) {
    return {};
  }
  const errors: { from?: QuietHoursError; until?: QuietHoursError } = {};
  if (!TIME_OF_DAY.test(form.from)) {
    errors.from = "format";
  }
  if (!TIME_OF_DAY.test(form.until)) {
    errors.until = "format";
  }
  if (!errors.from && !errors.until && form.from === form.until) {
    errors.until = "same";
  }
  return errors;
}

export function preferencesFromForm(form: PreferencesForm): NotificationPreferences {
  return {
    events: [...form.events],
    quiet_hours: form.hasQuietHours ? { starts_at: form.from, ends_at: form.until } : null,
  };
}

/** Every event at any hour: what having no choice stored means. */
export function isEverything(preferences: NotificationPreferences | null | undefined): boolean {
  const events = preferences?.events ?? ALL_EVENTS;
  return ALL_EVENTS.every((event) => events.includes(event)) && !preferences?.quiet_hours;
}

export function isSamePreferences(left: NotificationPreferences, right: NotificationPreferences): boolean {
  const events = (value: NotificationPreferences) => ALL_EVENTS.filter((event) => (value.events ?? ALL_EVENTS).includes(event));
  const quiet = (value: NotificationPreferences) => (value.quiet_hours ? `${value.quiet_hours.starts_at}-${value.quiet_hours.ends_at}` : "");
  return events(left).join() === events(right).join() && quiet(left) === quiet(right);
}

type Translate = (key: MessageKey, values?: Record<string, string | number>) => string;

/** One line for a list: "Everything, at any time" or "Only: handoffs · quiet 22:00–08:00". */
export function preferencesSummary(t: Translate, preferences: NotificationPreferences | null | undefined): string {
  if (isEverything(preferences)) {
    return t("notifications.preferences.summary.everything");
  }
  const events = ALL_EVENTS.filter((event) => (preferences?.events ?? ALL_EVENTS).includes(event));
  const what =
    events.length === ALL_EVENTS.length
      ? null
      : events.length === 0
        ? t("notifications.preferences.summary.nothing")
        : t("notifications.preferences.summary.events", {
            events: events.map((event) => t(EVENT_SHORT_LABELS[event])).join(", "),
          });
  const quiet = preferences?.quiet_hours
    ? t("notifications.preferences.summary.quiet", {
        from: preferences.quiet_hours.starts_at,
        until: preferences.quiet_hours.ends_at,
      })
    : null;
  return [what, quiet].filter((part): part is string => part !== null).join(" · ");
}

export type CheckOutcome = { tone: "success" | "error" | "info"; key: MessageKey };

/** How a check of a contact turned out, as a toast. */
export function contactCheckOutcome(result: NotificationCheckResult): CheckOutcome {
  if (result.delivery.status === "dead") {
    return { tone: "error", key: "notifications.contacts.testFailed" };
  }
  if (result.delivery.status === "pending") {
    return { tone: "info", key: "notifications.contacts.testPending" };
  }
  return result.is_simulated
    ? { tone: "info", key: "notifications.contacts.testSimulated" }
    : { tone: "success", key: "notifications.contacts.testDelivered" };
}

/** This browser's device in my list: the one it subscribed as, while it still holds that subscription. */
export function findThisDevice(
  devices: readonly PushDevice[],
  remembered: RememberedDevice | null,
  browserEndpoint: string | null,
): PushDevice | null {
  if (remembered === null || browserEndpoint === null || remembered.endpoint !== browserEndpoint) {
    return null;
  }
  return devices.find((device) => device.id === remembered.deviceId) ?? null;
}
