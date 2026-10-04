/**
 * Pure rules of the team inbox list: the view and filters in the URL, which
 * API answers them, and one row shape for both answers.
 *
 * The four work views (Needs a person, Requests, Mine, Unassigned) and
 * "All" come from GET …/inbox (one keyset page per view, with the channel
 * filter). Searching, a period, a status or test conversations are about
 * the whole history: they belong to "All" and are answered by the
 * conversation feed (GET …/conversations), which filters by them.
 */

import type { LocalDateText } from "@/components/insights/dates";
import type {
  ChannelKind,
  ConversationRating,
  ConversationStatus,
  ConversationSummaryView,
  MessageAuthor,
} from "@/components/insights/types";
import { DEFAULT_INBOX_VIEW, isInboxView, type InboxView } from "@/lib/navigation";

import {
  conversationApiQuery,
  DEFAULT_CONVERSATION_FILTERS,
  parseConversationFilters,
  type ConversationFilters,
  type ConversationPeriod,
} from "./conversationModel";
import type { AttachmentKind } from "./messageMedia";
import type { InboxHandoffSummary, InboxItemView, InboxRequestSummary, InboxViewCounts } from "./types";

export interface InboxFilters extends ConversationFilters {
  view: InboxView;
}

export const DEFAULT_INBOX_FILTERS: InboxFilters = { ...DEFAULT_CONVERSATION_FILTERS, view: DEFAULT_INBOX_VIEW };

/** Filters from the page URL; the history filters hold only on "All". */
export function parseInboxFilters(params: URLSearchParams): InboxFilters {
  const conversation = parseConversationFilters(params);
  const requested = params.get("view");
  const view = isInboxView(requested) ? requested : DEFAULT_INBOX_VIEW;
  return view === "all" ? { ...conversation, view } : { ...DEFAULT_CONVERSATION_FILTERS, channel: conversation.channel, view };
}

/** The URL query of filters ("" on the default view without filters), stable in key order. */
export function inboxFiltersQuery(filters: InboxFilters): string {
  const params = new URLSearchParams();
  if (filters.view !== DEFAULT_INBOX_VIEW) params.set("view", filters.view);
  if (filters.channel) params.set("channel", filters.channel);
  if (filters.view === "all") {
    if (filters.status) params.set("status", filters.status);
    if (filters.period !== "all") params.set("period", filters.period);
    if (filters.search.trim()) params.set("q", filters.search.trim());
    if (filters.includeTest) params.set("test", "1");
  }
  return params.toString();
}

/** Another view: the channel stays, the history filters stay only on "All". */
export function withView(filters: InboxFilters, view: InboxView): InboxFilters {
  return view === "all" ? { ...filters, view } : { ...DEFAULT_CONVERSATION_FILTERS, channel: filters.channel, view };
}

/** A search looks through every conversation, so it moves the list to "All". */
export function withSearch(filters: InboxFilters, search: string): InboxFilters {
  return { ...filters, view: search.trim() ? "all" : filters.view, search };
}

/** The history filters set on "All" (they send the list to the conversation feed). */
export function historyFilterCount(filters: InboxFilters): number {
  if (filters.view !== "all") {
    return 0;
  }
  return [filters.status !== null, filters.period !== "all", filters.search.trim() !== "", filters.includeTest].filter(Boolean)
    .length;
}

/** The filters shown on the Filters button (the search has its own field). */
export function sheetFilterCount(filters: InboxFilters): number {
  const history = filters.view === "all" ? [filters.status !== null, filters.period !== "all", filters.includeTest] : [];
  return [filters.channel !== null, ...history].filter(Boolean).length;
}

/** Whether the conversation feed answers (a search or a history filter on "All"). */
export function usesConversationFeed(filters: InboxFilters): boolean {
  return historyFilterCount(filters) > 0;
}

/** The filters of the sheet cleared; the search (in its own field) stays. */
export function clearedFilters(filters: InboxFilters): InboxFilters {
  return { ...DEFAULT_CONVERSATION_FILTERS, view: filters.view, search: filters.view === "all" ? filters.search : "" };
}

/** Back to the view alone: no channel, no history filters, no search. */
export function viewOnly(filters: InboxFilters): InboxFilters {
  return { ...DEFAULT_CONVERSATION_FILTERS, view: filters.view };
}

/** The query of GET …/inbox for a view. */
export function inboxApiQuery(filters: InboxFilters): { view: InboxView; channel?: ChannelKind } {
  return { view: filters.view, ...(filters.channel ? { channel: filters.channel } : {}) };
}

/** The query of GET …/conversations for a search or the history filters. */
export function feedApiQuery(filters: InboxFilters, today: LocalDateText) {
  return conversationApiQuery(filters, today);
}

export type { ConversationPeriod };

/** One conversation in the list, whichever API it came from. */
export interface InboxRow {
  id: string;
  contactName: string | null;
  contactPhone: string | null;
  channel: ChannelKind;
  language: string | null;
  status: ConversationStatus;
  isAfterHours: boolean;
  isSandbox: boolean;
  lastMessageText: string | null;
  /** What the last message carries besides text (a voice message, a photo…). */
  lastMessageAttachment: AttachmentKind | null;
  lastMessageAuthor: MessageAuthor | null;
  lastMessageAt: number;
  /** Undefined when the source does not say (the feed has no assignments). */
  assigneeUserId?: string | null;
  isAssignedAutomatically: boolean;
  noteCount: number;
  handoff: InboxHandoffSummary | null;
  request: InboxRequestSummary | null;
  rating: ConversationRating | null;
  /** Where the customer came from (a link's tag, an ad, the number dialled), when known. */
  acquisitionSource?: string | null;
}

export function rowFromInboxItem(item: InboxItemView): InboxRow {
  return {
    id: item.id,
    contactName: item.contact_name ?? null,
    contactPhone: item.contact_phone_number ?? null,
    channel: item.channel,
    language: item.language ?? null,
    status: item.status,
    isAfterHours: item.is_after_hours,
    // The inbox leaves test conversations out.
    isSandbox: false,
    lastMessageText: item.last_message_text ?? null,
    lastMessageAttachment: item.last_message_attachment ?? null,
    lastMessageAuthor: item.last_message_author ?? null,
    lastMessageAt: item.last_message_at,
    assigneeUserId: item.assignee_user_id ?? null,
    isAssignedAutomatically: item.is_assigned_automatically,
    noteCount: item.note_count,
    handoff: item.handoff ?? null,
    request: item.request ?? null,
    rating: null,
    acquisitionSource: item.acquisition_source ?? null,
  };
}

export function rowFromConversation(item: ConversationSummaryView): InboxRow {
  return {
    id: item.id,
    contactName: item.contact_name ?? null,
    contactPhone: item.contact_phone_number ?? null,
    channel: item.channel,
    language: item.language ?? null,
    status: item.status,
    isAfterHours: item.is_after_hours,
    isSandbox: item.is_sandbox,
    lastMessageText: item.last_message_text ?? null,
    lastMessageAttachment: item.last_message_attachment ?? null,
    lastMessageAuthor: item.last_message_author ?? null,
    lastMessageAt: item.last_message_at,
    isAssignedAutomatically: false,
    noteCount: 0,
    handoff: null,
    request: null,
    rating: item.rating ?? null,
  };
}

/** The number on a view's tab; "All" has none (it is the whole history). */
export function viewCount(view: InboxView, counts: InboxViewCounts | null | undefined): number | undefined {
  if (!counts || view === "all") {
    return undefined;
  }
  return counts[view];
}
