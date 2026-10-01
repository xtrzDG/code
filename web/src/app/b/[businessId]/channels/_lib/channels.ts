/**
 * Pure helpers of the Channels page: which channels can be connected, their
 * state badges, the connect form per channel and call-forwarding codes.
 */

import type { RequestBody, Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";

export type ChannelKind = Schema<"ChannelKind">;
export type ChannelStatus = Schema<"ChannelStatus">;
export type ChannelView = Schema<"ChannelView">;
export type CallForwardingCondition = Schema<"CallForwardingCondition">;
export type ConnectChannelBody = RequestBody<"/v1/businesses/{business_id}/channels/{channel}", "put">;

/** Channels an owner can connect now, in the order the page shows them. */
export const CONNECTABLE_CHANNELS = ["web_chat", "telegram", "whatsapp", "instagram", "messenger", "phone"] as const;

export type ConnectableChannel = (typeof CONNECTABLE_CHANNELS)[number];

export function isConnectableChannel(kind: string): kind is ConnectableChannel {
  return (CONNECTABLE_CHANNELS as readonly string[]).includes(kind);
}

/** The channel's name in the API path ("web" is the website chat). */
export function channelPathName(kind: ConnectableChannel): string {
  return kind === "web_chat" ? "web" : kind;
}

/** The channel of a kind, if the business has one. */
export function findChannel(channels: readonly ChannelView[] | undefined, kind: ChannelKind): ChannelView | undefined {
  return channels?.find((channel) => channel.channel === kind);
}

/** What the page shows for a channel: never connected, or its status. */
export type ChannelState = "not_connected" | ChannelStatus;

export function channelState(channel: ChannelView | undefined): ChannelState {
  return channel ? channel.status : "not_connected";
}

export const CHANNEL_STATE_TONES: Record<ChannelState, BadgeTone> = {
  not_connected: "neutral",
  pending: "warning",
  connected: "success",
  disabled: "neutral",
  error: "danger",
};

/** Whether the channel works or is on its way (it can be disconnected). */
export function isChannelOn(channel: ChannelView | undefined): boolean {
  return channel !== undefined && channel.status !== "disabled";
}

/** Replace (or add) one channel in the list after a connect or disconnect. */
export function upsertChannel(channels: readonly ChannelView[] | undefined, updated: ChannelView): ChannelView[] {
  const list = [...(channels ?? [])];
  const index = list.findIndex((channel) => channel.channel === updated.channel);
  if (index >= 0) {
    list[index] = updated;
  } else {
    list.push(updated);
  }
  return list;
}

/** "@cafe_bot" for a Telegram bot; other accounts as they are. */
export function accountLabel(kind: ChannelKind, accountId: string | null | undefined): string | null {
  if (!accountId) {
    return null;
  }
  return kind === "telegram" && !accountId.startsWith("@") ? `@${accountId}` : accountId;
}

// --- Connect form ------------------------------------------------------------

export interface ConnectForm {
  botToken: string;
  phoneNumberId: string;
  businessAccountId: string;
  pageId: string;
  pageAccessToken: string;
  phoneNumber: string;
  countryHint: string;
}

export type ConnectField = keyof ConnectForm;

export const EMPTY_CONNECT_FORM: ConnectForm = {
  botToken: "",
  phoneNumberId: "",
  businessAccountId: "",
  pageId: "",
  pageAccessToken: "",
  phoneNumber: "",
  countryHint: "",
};

/** Fields each channel asks for (the website chat needs none). */
export const CHANNEL_FIELDS: Record<ConnectableChannel, readonly ConnectField[]> = {
  web_chat: [],
  telegram: ["botToken"],
  whatsapp: ["phoneNumberId", "businessAccountId"],
  instagram: ["pageId", "pageAccessToken"],
  messenger: ["pageId", "pageAccessToken"],
  phone: ["phoneNumber", "countryHint"],
};

/** Why a field was refused; the page maps these to texts. */
export type ConnectFieldError = "required" | "botToken" | "digits" | "pageToken";

/** Token from @BotFather: "<bot id>:<35 characters>" (the API checks the same shape). */
const BOT_TOKEN = /^[0-9]{5,20}:[A-Za-z0-9_-]{30,100}$/;
/** Meta object ids (phone number id, business account id, page id). */
const META_ID = /^[0-9]{1,32}$/;
const MIN_PAGE_TOKEN_LENGTH = 20;
const MAX_PAGE_TOKEN_LENGTH = 1024;

function isPageToken(token: string): boolean {
  return (
    token.length >= MIN_PAGE_TOKEN_LENGTH &&
    token.length <= MAX_PAGE_TOKEN_LENGTH &&
    /^[\x21-\x7e]+$/.test(token)
  );
}

export type ConnectFormResult =
  | { ok: true; body: ConnectChannelBody }
  | { ok: false; errors: Partial<Record<ConnectField, ConnectFieldError>> };

/**
 * The PUT body for a channel from the form, or the fields to fix. Values
 * are trimmed; only the channel's own fields are sent.
 */
export function buildConnectBody(kind: ConnectableChannel, form: ConnectForm): ConnectFormResult {
  const value = (field: ConnectField) => form[field].trim();
  const errors: Partial<Record<ConnectField, ConnectFieldError>> = {};

  switch (kind) {
    case "web_chat":
      return { ok: true, body: {} };
    case "telegram": {
      const token = value("botToken").replace(/\s+/g, "");
      if (token === "") {
        errors.botToken = "required";
      } else if (!BOT_TOKEN.test(token)) {
        errors.botToken = "botToken";
      }
      return Object.keys(errors).length > 0 ? { ok: false, errors } : { ok: true, body: { bot_token: token } };
    }
    case "whatsapp": {
      const phoneNumberId = value("phoneNumberId");
      const accountId = value("businessAccountId");
      if (phoneNumberId === "") {
        errors.phoneNumberId = "required";
      } else if (!META_ID.test(phoneNumberId)) {
        errors.phoneNumberId = "digits";
      }
      if (accountId !== "" && !META_ID.test(accountId)) {
        errors.businessAccountId = "digits";
      }
      if (Object.keys(errors).length > 0) {
        return { ok: false, errors };
      }
      return {
        ok: true,
        body: {
          phone_number_id: phoneNumberId,
          ...(accountId ? { whatsapp_business_account_id: accountId } : {}),
        },
      };
    }
    case "instagram":
    case "messenger": {
      const pageId = value("pageId");
      const token = value("pageAccessToken");
      if (pageId === "") {
        errors.pageId = "required";
      } else if (!META_ID.test(pageId)) {
        errors.pageId = "digits";
      }
      if (token === "") {
        errors.pageAccessToken = "required";
      } else if (!isPageToken(token)) {
        errors.pageAccessToken = "pageToken";
      }
      return Object.keys(errors).length > 0
        ? { ok: false, errors }
        : { ok: true, body: { page_id: pageId, page_access_token: token } };
    }
    case "phone": {
      const phoneNumber = value("phoneNumber");
      const countryHint = value("countryHint").toUpperCase();
      if (phoneNumber === "") {
        errors.phoneNumber = "required";
        return { ok: false, errors };
      }
      return {
        ok: true,
        body: { phone_number: phoneNumber, ...(/^[A-Z]{2}$/.test(countryHint) ? { country_hint: countryHint } : {}) },
      };
    }
  }
}

// --- Call forwarding -----------------------------------------------------------

/** Order of the forwarding codes: the three conditions, then "switch off". */
export const FORWARDING_CONDITIONS: readonly CallForwardingCondition[] = ["no_answer", "busy", "unreachable", "cancel_all"];

export function sortForwardingCodes<T extends { condition: CallForwardingCondition }>(codes: readonly T[]): T[] {
  return [...codes].sort(
    (left, right) => FORWARDING_CONDITIONS.indexOf(left.condition) - FORWARDING_CONDITIONS.indexOf(right.condition),
  );
}

/**
 * A link that opens the phone's dialer with a GSM code: "#" must be
 * escaped in tel: URIs ("**61*+995…#" -> "tel:**61*+995…%23").
 */
export function dialHref(dialCode: string): string {
  return `tel:${dialCode.replace(/#/g, "%23")}`;
}

// --- Staff Telegram link -----------------------------------------------------

/** "ABCDE12345" -> "ABCDE 12345" for reading aloud or typing. */
export function formatLinkCode(code: string): string {
  return code.replace(/(.{5})(?=.)/g, "$1 ");
}

/** What a manager sends to the platform bot without the deep link. */
export function startCommand(code: string): string {
  return `/start ${code}`;
}

/** Languages offered for a manager's notifications: the owner's first, then the business languages. */
export function notificationLanguages(ownerLanguage: string, languages: readonly string[]): string[] {
  return [...new Set([ownerLanguage, ...languages])];
}

/** Whether a plan (its channel list) covers a channel; unknown plans cover everything. */
export function isChannelInPlan(planChannels: readonly ChannelKind[] | undefined, kind: ChannelKind): boolean {
  return planChannels === undefined || planChannels.includes(kind);
}

// --- Website chat look -----------------------------------------------------------

export type WidgetPosition = Schema<"WidgetPosition">;

/** The widget's own accent colour (widget.js DEFAULT_ACCENT). */
export const WIDGET_DEFAULT_COLOR = "#4f46e5";

/** Brand colours offered as one-click choices (each readable with white or dark text). */
export const WIDGET_COLOR_PRESETS = ["#4f46e5", "#0f766e", "#15803d", "#b91c1c", "#c2410c", "#be185d", "#1d4ed8", "#111827"] as const;

export const WIDGET_POSITIONS: readonly WidgetPosition[] = ["right", "left"];

/**
 * "#0F766E", "0f766e" or "#abc" as the API's six-digit form ("#0f766e");
 * null when it is not a hex colour.
 */
export function normalizeHexColor(value: string): string | null {
  const text = value.trim().replace(/^#/, "");
  if (/^[0-9a-fA-F]{6}$/.test(text)) {
    return `#${text.toLowerCase()}`;
  }
  if (/^[0-9a-fA-F]{3}$/.test(text)) {
    return `#${[...text.toLowerCase()].map((digit) => digit + digit).join("")}`;
  }
  return null;
}

/** Text colour that stays readable on the accent (the widget uses the same rule). */
export function readableTextColor(hexColor: string): "#111827" | "#ffffff" {
  const hex = normalizeHexColor(hexColor) ?? WIDGET_DEFAULT_COLOR;
  const [red, green, blue] = [1, 3, 5].map((offset) => {
    const value = parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
  });
  const luminance = 0.2126 * (red ?? 0) + 0.7152 * (green ?? 0) + 0.0722 * (blue ?? 0);
  // The higher WCAG contrast: with white 1.05/(L+0.05), with #111827 (L≈0.0093) (L+0.05)/0.0593.
  return 1.05 / (luminance + 0.05) >= (luminance + 0.05) / 0.0593 ? "#ffffff" : "#111827";
}

export interface WidgetLook {
  color: string;
  position: WidgetPosition;
}

/** The saved look of the website chat, with the widget's defaults filled in. */
export function savedWidgetLook(channel: Pick<ChannelView, "widget_color" | "widget_position"> | undefined): WidgetLook {
  return {
    color: normalizeHexColor(channel?.widget_color ?? "") ?? WIDGET_DEFAULT_COLOR,
    position: channel?.widget_position ?? "right",
  };
}

export function isSameWidgetLook(left: WidgetLook, right: WidgetLook): boolean {
  return normalizeHexColor(left.color) === normalizeHexColor(right.color) && left.position === right.position;
}

/**
 * The demo page with the chosen (maybe unsaved) colour, corner and the
 * interface language: /widget/demo?business_id=…&color=…&position=…&language=…
 */
export function buildWidgetPreviewUrl(demoUrl: string, look: WidgetLook, language: string): string {
  const url = new URL(demoUrl);
  const color = normalizeHexColor(look.color);
  if (color) {
    url.searchParams.set("color", color);
  }
  url.searchParams.set("position", look.position);
  url.searchParams.set("language", language);
  return url.toString();
}

// --- Google Calendar return ------------------------------------------------------

export const CALENDAR_FAILURE_REASONS = ["access_denied", "link_expired", "no_offline_access", "provider_error"] as const;

export type CalendarFailureReason = (typeof CALENDAR_FAILURE_REASONS)[number] | "unknown";

export type CalendarReturn = { kind: "connected" } | { kind: "error"; reason: CalendarFailureReason };

/**
 * What the API's Google callback said when it sent the owner back here
 * (?calendar=connected or ?calendar=error&reason=…); null otherwise.
 */
export function readCalendarReturn(search: string): CalendarReturn | null {
  const params = new URLSearchParams(search);
  const calendar = params.get("calendar");
  if (calendar === "connected") {
    return { kind: "connected" };
  }
  if (calendar !== "error") {
    return null;
  }
  const reason = params.get("reason");
  return {
    kind: "error",
    reason: (CALENDAR_FAILURE_REASONS as readonly string[]).includes(reason ?? "")
      ? (reason as CalendarFailureReason)
      : "unknown",
  };
}

/** The query without the calendar notice, to put back into the address bar. */
export function withoutCalendarReturn(search: string): string {
  const params = new URLSearchParams(search);
  params.delete("calendar");
  params.delete("reason");
  return params.toString();
}
