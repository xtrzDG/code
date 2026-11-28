/**
 * Pure helpers of the Channels page: which channels can be connected, their
 * state badges, plans, call-forwarding codes and the staff Telegram link.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";
import { formatPhone } from "@/lib/phone";

export type ChannelKind = Schema<"ChannelKind">;
type ChannelStatus = Schema<"ChannelStatus">;
export type ChannelView = Schema<"ChannelView">;
export type CallForwardingCondition = Schema<"CallForwardingCondition">;
export type StarCodeCondition = Schema<"StarCodeCondition">;

/** Channels an owner can connect now, in the order the page shows them. */
export const CONNECTABLE_CHANNELS = ["web_chat", "telegram", "whatsapp", "instagram", "messenger", "phone"] as const;

export type ConnectableChannel = (typeof CONNECTABLE_CHANNELS)[number];

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

/**
 * A connected channel customers cannot be sent a link to: the platform never
 * told its public address, so Share and the chat page skip it (the API's
 * `link_state`, the same rule its share links follow). An error says more.
 */
export function isLinkMissing(channel: ChannelView | undefined): boolean {
  return channel?.status === "connected" && channel.link_state === "missing_public_address";
}

/**
 * The list right after a disconnect (the API answers 204): the channel is
 * off and its credential gone, as the server keeps it; a reload confirms.
 */
export function markChannelDisabled(channels: readonly ChannelView[] | undefined, kind: ChannelKind): ChannelView[] {
  return (channels ?? []).map((channel) =>
    channel.channel === kind ? { ...channel, status: "disabled", has_credential: false, account_id: null } : channel,
  );
}

/** Replace (or add) one channel in the list after a connect. */
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
  if (kind === "phone") {
    // The assistant's line as people read it: "+995 32 200 00 00".
    return formatPhone(accountId);
  }
  return kind === "telegram" && !accountId.startsWith("@") ? `@${accountId}` : accountId;
}

// --- Call forwarding -----------------------------------------------------------

/** Order of the forwarding codes: the three conditions, then "switch off". */
const FORWARDING_CONDITIONS: readonly CallForwardingCondition[] = ["no_answer", "busy", "unreachable", "cancel_all"];

/** Order of a carrier's star codes (Verizon's *71, then *73): forwarding, then "switch off". */
const STAR_CODE_CONDITIONS: readonly StarCodeCondition[] = ["no_answer_or_busy", "cancel_all"];

function sortByCondition<C extends string, T extends { condition: C }>(codes: readonly T[], order: readonly C[]): T[] {
  return [...codes].sort((left, right) => order.indexOf(left.condition) - order.indexOf(right.condition));
}

export function sortForwardingCodes<T extends { condition: CallForwardingCondition }>(codes: readonly T[]): T[] {
  return sortByCondition(codes, FORWARDING_CONDITIONS);
}

export function sortStarCodes<T extends { condition: StarCodeCondition }>(codes: readonly T[]): T[] {
  return sortByCondition(codes, STAR_CODE_CONDITIONS);
}

/**
 * A link that opens the phone's dialer with a forwarding code: "#" must be
 * escaped in tel: URIs ("**61*+995…#" -> "tel:**61*+995…%23"); a star code
 * has none ("*712125550123" -> "tel:*712125550123").
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
