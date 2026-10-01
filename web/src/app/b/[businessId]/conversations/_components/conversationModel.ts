/**
 * Pure rules of the conversation feed and card: filters (some sent to the
 * API, the rest applied here), search, transcript grouping and usage totals.
 */

import { addDays, localDateOf, type LocalDateText } from "@/components/insights/dates";
import type {
  ChannelKind,
  ConversationStatus,
  ConversationSummaryView,
  MessageAuthor,
  MessageView,
} from "@/components/insights/types";

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
  /** Sent to the API. */
  channel: ChannelKind | null;
  /** Sent to the API (`include_sandbox`). */
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

/** Lower case without accents, for matching typed text in any script. */
export function normalizeText(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLocaleLowerCase()
    .trim();
}

/** Name, phone (by digits, any formatting) or the last message contains the query. */
export function matchesSearch(
  conversation: Pick<ConversationSummaryView, "contact_name" | "contact_phone_number" | "last_message_text">,
  query: string,
): boolean {
  const needle = normalizeText(query);
  if (!needle) {
    return true;
  }
  const haystack = normalizeText([conversation.contact_name ?? "", conversation.last_message_text ?? ""].join(" "));
  if (haystack.includes(needle)) {
    return true;
  }
  const digits = query.replace(/\D/g, "");
  return digits.length >= 3 && (conversation.contact_phone_number ?? "").replace(/\D/g, "").includes(digits);
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

/** The filters the API does not apply: status, period (by last message) and search. */
export function filterConversations<T extends ConversationSummaryView>(
  conversations: readonly T[],
  filters: ConversationFilters,
  context: { today: LocalDateText; timeZone: string },
): T[] {
  const from = periodStart(filters.period, context.today);
  return conversations.filter(
    (conversation) =>
      (filters.status === null || conversation.status === filters.status) &&
      (from === null || localDateOf(conversation.last_message_at, context.timeZone) >= from) &&
      matchesSearch(conversation, filters.search),
  );
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

/** Up to two letters for an avatar: "Nino Beridze" -> "NB", "+995…" -> "#". */
export function initialsOf(name: string | null | undefined): string {
  const words = (name ?? "").trim().split(/\s+/u).filter((word) => /\p{L}/u.test(word));
  if (words.length === 0) {
    return "#";
  }
  return words
    .slice(0, 2)
    .map((word) => capitalLetter([...word][0] ?? ""))
    .join("");
}

/** Upper case, except Georgian: its capitals (Mtavruli) are not used in names. */
function capitalLetter(letter: string): string {
  const upper = letter.toLocaleUpperCase();
  return /[\u1C90-\u1CBF]/u.test(upper) ? letter : upper;
}
