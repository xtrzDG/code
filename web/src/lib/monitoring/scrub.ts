/**
 * What the cabinet sends to Sentry: no request (cookies, headers, bodies,
 * query strings), no user, no breadcrumbs (they hold what owners typed),
 * and e-mail addresses, phone numbers and the keys of guests' booking
 * links (/r/{token}) masked in error texts and transaction names.
 */

import { withoutBookingToken } from "../bookingPage/paths";

const EMAIL_PATTERN = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
// Seven or more digits, with the separators phone numbers are written with.
const PHONE_PATTERN = /\+?\d[\d\s().-]{5,}\d/g;

export interface MonitoringEvent {
  request?: unknown;
  user?: unknown;
  breadcrumbs?: unknown;
  message?: string;
  transaction?: string;
  exception?: { values?: { value?: string }[] };
}

export function redactText(text: string): string {
  return withoutBookingToken(text).replace(EMAIL_PATTERN, "[email]").replace(PHONE_PATTERN, "[number]");
}

/** The event without personal data; Sentry's `beforeSend` and `beforeSendTransaction`. */
export function scrubEvent<Event extends MonitoringEvent>(event: Event): Event {
  delete event.request;
  delete event.user;
  delete event.breadcrumbs;
  if (typeof event.message === "string") {
    event.message = redactText(event.message);
  }
  if (typeof event.transaction === "string") {
    // A guest's booking address is the key to the booking.
    event.transaction = withoutBookingToken(event.transaction.split("?")[0] ?? "");
  }
  for (const value of event.exception?.values ?? []) {
    if (typeof value.value === "string") {
      value.value = redactText(value.value);
    }
  }
  return event;
}
