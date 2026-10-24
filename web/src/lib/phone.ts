/**
 * Phone numbers as people read them: the API keeps E.164 ("+995555000001"),
 * the cabinet shows "+995 555 00 00 01", grouped the way the number's
 * country writes it (libphonenumber-js with its small "min" metadata).
 * Anything that is not a phone number we know comes back as it was, so a
 * Telegram handle or an e-mail address passed by mistake is never mangled.
 *
 * Phone numbers are written left to right even on a right-to-left page:
 * render them inside `dir="ltr"` (or a <bdi>).
 */

import { parsePhoneNumberFromString } from "libphonenumber-js/min";

/** "+995555000001" -> "+995 555 00 00 01"; other text unchanged. */
export function formatPhone(e164: string | null | undefined): string {
  const text = (e164 ?? "").trim();
  if (!/^\+\d{6,15}$/.test(text.replace(/[\s-]/g, ""))) {
    return text;
  }
  const parsed = parsePhoneNumberFromString(text);
  return parsed?.isPossible() ? parsed.formatInternational() : text;
}

/** A contact address shown to people: phone numbers grouped, e-mails and handles as they are. */
export function formatContactAddress(channel: string, address: string): string {
  return channel === "email" || channel === "telegram" ? address : formatPhone(address);
}
