/**
 * Pure rules of the conversation feed and card: filters (all applied by the
 * API), transcript grouping, usage totals, calls and the staff reply box.
 */

import { BFF_BASE_PATH } from "@/api/client";
import { addDays, localDateOf, type LocalDateText } from "@/components/insights/dates";
import type {
  CallOutcome,
  ChannelKind,
  ConversationStatus,
  MessageAuthor,
  MessageView,
  StaffReplyBlock,
  StaffReplyView,
} from "@/components/insights/types";
import type { MessageKey } from "@/i18n/translate";

export const CONVERSATION_PERIODS = ["all", "today", "7d", "30d"] as const;
export type ConversationPeriod = (typeof CONVERSATION_PERIODS)[number];

const CHANNELS: readonly ChannelKind[] = [
  "phone",
  "whatsapp",
  "instagram",
  "messenger",
  "telegram",
  "web_chat",
  "viber",
  "owner_test",
];
const STATUSES: readonly ConversationStatus[] = ["open", "handoff", "closed"];

export interface ConversationFilters {
  channel: ChannelKind | null;
  /** `include_sandbox`: the test chat and autotests. */
  includeTest: boolean;
  status: ConversationStatus | null;
  period: ConversationPeriod;
  search: string;
}

export const DEFAULT_CONVERSATION_FILTERS: ConversationFilters = {
  channel: null,
  includeTest: false,
  status: null,
  period: "all",
  search: "",
};

function pick<T extends string>(value: string | null, allowed: readonly T[]): T | null {
  return value !== null && (allowed as readonly string[]).includes(value) ? (value as T) : null;
}

/** Filters from the page URL; unknown values fall back to the defaults. */
export function parseConversationFilters(params: URLSearchParams): ConversationFilters {
  return {
    channel: pick(params.get("channel"), CHANNELS),
    includeTest: params.get("test") === "1",
    status: pick(params.get("status"), STATUSES),
    period: pick(params.get("period"), CONVERSATION_PERIODS) ?? "all",
    search: (params.get("q") ?? "").slice(0, 200),
  };
}

/** The URL query of filters ("" for the defaults), stable in key order. */
export function conversationFiltersQuery(filters: ConversationFilters): string {
  const params = new URLSearchParams();
  if (filters.channel) params.set("channel", filters.channel);
  if (filters.status) params.set("status", filters.status);
  if (filters.period !== "all") params.set("period", filters.period);
  if (filters.search.trim()) params.set("q", filters.search.trim());
  if (filters.includeTest) params.set("test", "1");
  return params.toString();
}

export function hasActiveFilters(filters: ConversationFilters): boolean {
  return conversationFiltersQuery(filters) !== "";
}

/** The first local date of a period ending today, or null for all time. */
export function periodStart(period: ConversationPeriod, today: LocalDateText): LocalDateText | null {
  switch (period) {
    case "today":
      return today;
    case "7d":
      return addDays(today, -6);
    case "30d":
      return addDays(today, -29);
    default:
      return null;
  }
}

/** The API query of the feed filters (the period as local dates of the business). */
export function conversationApiQuery(
  filters: ConversationFilters,
  today: LocalDateText,
): { channel?: ChannelKind; status?: ConversationStatus; from?: LocalDateText; search?: string; include_sandbox?: "true" } {
  const from = periodStart(filters.period, today);
  const search = filters.search.trim();
  return {
    ...(filters.channel ? { channel: filters.channel } : {}),
    ...(filters.status ? { status: filters.status } : {}),
    ...(from ? { from } : {}),
    ...(search ? { search } : {}),
    ...(filters.includeTest ? { include_sandbox: "true" as const } : {}),
  };
}

export interface MessageDay {
  date: LocalDateText;
  messages: MessageView[];
}

/** Messages in time order, split by local day of the business. */
export function groupMessagesByDay(messages: readonly MessageView[], timeZone: string): MessageDay[] {
  const days: MessageDay[] = [];
  for (const message of [...messages].sort((left, right) => left.created_at - right.created_at)) {
    const date = localDateOf(message.created_at, timeZone);
    const last = days.at(-1);
    if (last && last.date === date) {
      last.messages.push(message);
    } else {
      days.push({ date, messages: [message] });
    }
  }
  return days;
}

/** Customers on one side, the business (assistant, staff) on the other, system notes centered. */
export function messageSide(author: MessageAuthor): "start" | "end" | "center" {
  switch (author) {
    case "customer":
      return "start";
    case "system":
      return "center";
    default:
      return "end";
  }
}

/** Tool JSON indented for reading; text that is not JSON is shown as it is. */
export function prettyJson(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

export interface UsageTotals {
  inputTokens: number;
  outputTokens: number;
  costMicroUsd: number;
}

export function usageTotals(messages: readonly Pick<MessageView, "input_tokens" | "output_tokens" | "cost_micro_usd">[]): UsageTotals {
  return messages.reduce<UsageTotals>(
    (totals, message) => ({
      inputTokens: totals.inputTokens + message.input_tokens,
      outputTokens: totals.outputTokens + message.output_tokens,
      costMicroUsd: totals.costMicroUsd + message.cost_micro_usd,
    }),
    { inputTokens: 0, outputTokens: 0, costMicroUsd: 0 },
  );
}

/**
 * Up to two letters for an avatar: "Nino Beridze" -> "NB", "+995…" -> "#".
 * Arabic script takes one: its letters join into a different shape side by
 * side, and the second word often starts with the article "ال".
 */
export function initialsOf(name: string | null | undefined): string {
  const words = (name ?? "").trim().split(/\s+/u).filter((word) => /\p{L}/u.test(word));
  if (words.length === 0) {
    return "#";
  }
  const isArabicScript = /^\p{Script=Arabic}/u.test(words[0] ?? "");
  return words
    .slice(0, isArabicScript ? 1 : 2)
    .map((word) => capitalLetter([...word][0] ?? ""))
    .join("");
}

/** Upper case, except Georgian: its capitals (Mtavruli) are not used in names. */
function capitalLetter(letter: string): string {
  const upper = letter.toLocaleUpperCase();
  return /[\u1C90-\u1CBF]/u.test(upper) ? letter : upper;
}

/** "1:35" for a call of 95 seconds, "1:02:03" past an hour. */
export function formatCallDuration(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const rest = String(whole % 60).padStart(2, "0");
  return hours > 0 ? `${hours}:${String(minutes).padStart(2, "0")}:${rest}` : `${minutes}:${rest}`;
}

export const CALL_OUTCOMES: Record<CallOutcome, MessageKey> = {
  booking: "conversations.calls.outcomes.booking",
  lead: "conversations.calls.outcomes.lead",
  handoff: "conversations.calls.outcomes.handoff",
  unanswered_question: "conversations.calls.outcomes.unanswered_question",
  information: "conversations.calls.outcomes.information",
  abandoned: "conversations.calls.outcomes.abandoned",
};

/**
 * Address of a call's recording behind the cabinet's API proxy: the audio
 * player loads it itself (only when someone presses play), with the session
 * the proxy adds; every playback is written to the audit log.
 */
export function callRecordingUrl(businessId: string, callId: string): string {
  return `${BFF_BASE_PATH}/v1/businesses/${encodeURIComponent(businessId)}/calls/${encodeURIComponent(callId)}/recording`;
}

export const REPLY_BLOCKS: Record<StaffReplyBlock, MessageKey> = {
  voice_call: "conversations.reply.blocked.voice_call",
  test_conversation: "conversations.reply.blocked.test_conversation",
  window_closed: "conversations.reply.blocked.window_closed",
  unsupported_channel: "conversations.reply.blocked.unsupported_channel",
  channel_disconnected: "conversations.reply.blocked.channel_disconnected",
};

/** The longest staff message the API accepts. */
export const MAX_REPLY_LENGTH = 4000;

/** A staff reply worth sending: some visible text within the limit. */
export function isSendableReply(text: string): boolean {
  return text.trim().length > 0 && text.length <= MAX_REPLY_LENGTH;
}

/** Whether the 24-hour window closes within the hour (warn staff to hurry). */
export function isWindowClosingSoon(closesAt: number | null | undefined, nowMs: number): boolean {
  if (closesAt === null || closesAt === undefined) {
    return false;
  }
  const leftMs = closesAt / 1000 - nowMs;
  return leftMs > 0 && leftMs <= 60 * 60 * 1000;
}

/**
 * The staff text as the WhatsApp template's body parameter, as the API
 * sends it: one line, runs of spaces and line breaks become single spaces.
 */
export function templateReplyText(text: string): string {
  return text.split(/\s+/u).filter(Boolean).join(" ");
}

/** Characters (not UTF-16 units) of a template reply, as the API counts them. */
export function templateReplyLength(text: string): number {
  return [...templateReplyText(text)].length;
}

/** A reply that fits the template's single parameter. */
export function isSendableTemplateReply(text: string, maxLength: number): boolean {
  const length = templateReplyLength(text);
  return length > 0 && length <= maxLength;
}

/**
 * A WhatsApp template language ("pt_BR") by name in the interface language
 * ("Brazilian Portuguese (pt_BR)"); the code alone when Intl does not know it.
 */
export function templateLanguageName(code: string, locale: string): string {
  try {
    const name = new Intl.DisplayNames([locale], { type: "language" }).of(code.replace("_", "-"));
    return name && name !== code && name !== code.replace("_", "-") ? `${name} (${code})` : code;
  } catch {
    return code;
  }
}

/** The owner's WhatsApp template that carries staff text once the 24-hour window has closed, or null. */
export function offeredTemplate(reply: StaffReplyView): NonNullable<StaffReplyView["template"]> | null {
  return !reply.is_available && reply.block === "window_closed" ? (reply.template ?? null) : null;
}

/** Whether the reply box takes text now: freely, or in the owner's template. */
export function canReplyFromCard(reply: StaffReplyView | null | undefined): boolean {
  return reply != null && (reply.is_available || offeredTemplate(reply) !== null);
}
