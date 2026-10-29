/**
 * Pure rules of where an owner's summaries arrive (Reports → Your
 * summaries): e-mail, devices, a Telegram chat of the platform bot and
 * WhatsApp from the platform's number. The API refuses a channel that
 * cannot reach the owner; these rules keep the switches from offering it.
 */

import type { Schema } from "@/api/types";

export type DigestChannel = Schema<"DigestChannel">;
export type DigestPreferencesView = Schema<"DigestPreferencesView">;

/** The channels in the order the API keeps them. */
const DIGEST_CHANNELS: readonly DigestChannel[] = ["email", "push", "telegram", "whatsapp"];

/** The chosen channels with one switched on or off, in the API's order. */
export function withChannel(channels: readonly DigestChannel[], channel: DigestChannel, isOn: boolean): DigestChannel[] {
  const chosen = new Set(channels);
  if (isOn) {
    chosen.add(channel);
  } else {
    chosen.delete(channel);
  }
  return DIGEST_CHANNELS.filter((item) => chosen.has(item));
}

/** Whether a channel can be switched on (one that is on can always be switched off). */
export function canTurnOn(preferences: DigestPreferencesView, channel: DigestChannel): boolean {
  switch (channel) {
    case "email":
      return Boolean(preferences.email) && preferences.is_email_ready;
    case "push":
      return true;
    case "telegram":
      return preferences.is_telegram_ready && preferences.telegram_chats.length > 0;
    case "whatsapp":
      return preferences.is_whatsapp_ready;
  }
}

/** The chat Telegram summaries go to: the stored one while it is linked, else the first linked one. */
export function telegramChatFor(preferences: DigestPreferencesView): string | null {
  const linked = preferences.telegram_chats.map((chat) => chat.address);
  if (preferences.telegram_chat && linked.includes(preferences.telegram_chat)) {
    return preferences.telegram_chat;
  }
  return linked[0] ?? null;
}

/** The number WhatsApp summaries go to, to start the field with: the stored one, else the sign-in phone. */
export function whatsappNumberFor(preferences: DigestPreferencesView): string {
  return preferences.whatsapp_number ?? preferences.suggested_whatsapp_number ?? "";
}

const E164 = /^\+[1-9]\d{6,14}$/;

/** A typed WhatsApp number as E.164 ("+995 555 12-34-56" -> "+995555123456"); null when it is not one. */
export function normalizeWhatsAppNumber(text: string): string | null {
  const compact = text.replace(/[\s().-]/g, "");
  const withPlus = compact.startsWith("00") ? `+${compact.slice(2)}` : compact;
  return E164.test(withPlus) ? withPlus : null;
}
