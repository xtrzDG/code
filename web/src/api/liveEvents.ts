/**
 * What the live event stream of a business reports, and which cached
 * queries each change makes out of date. Events name changes by id only;
 * the cabinet reloads the touched lists through the normal API (which
 * checks access and audits views), so nothing here holds customer data.
 */

import type { ServerSentEvent } from "./eventStreamParser";
import type { QueryKey } from "./queryKey";
import { queryKeys } from "./queryKeys";

export const LIVE_EVENT_NAMES = [
  "handoff.created",
  "handoff.resolved",
  "conversation.message",
  "conversation.assigned",
  "conversation.note",
  "lead.created",
  "lead.changed",
  "booking.created",
  "booking.changed",
  "channel.error",
  "channel.changed",
  "autotest.progress",
  "knowledge_import.progress",
] as const;

export type LiveEventName = (typeof LIVE_EVENT_NAMES)[number];

/** Messages of the stream itself. */
export const STREAM_READY = "stream.ready";
export const STREAM_RESYNC = "stream.resync";

export interface LiveEvent {
  id: string | null;
  event: LiveEventName;
  /** Prefixed ids of what changed (`handoff_…`, `conversation_…`). */
  ids: string[];
  /** When it happened (UNIX microseconds). */
  occurredAt: number;
}

export interface StreamTimings {
  heartbeatSeconds: number;
  lifetimeSeconds: number;
}

const KNOWN_EVENTS: ReadonlySet<string> = new Set(LIVE_EVENT_NAMES);

function readJson(data: string): Record<string, unknown> | null {
  try {
    const value: unknown = JSON.parse(data);
    return value !== null && typeof value === "object" ? (value as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

/** A change of the business, or null for anything this cabinet does not know. */
export function readLiveEvent(message: ServerSentEvent): LiveEvent | null {
  if (!KNOWN_EVENTS.has(message.event)) {
    return null;
  }
  const data = readJson(message.data) ?? {};
  const ids = Array.isArray(data.ids) ? data.ids.filter((id): id is string => typeof id === "string") : [];
  return {
    id: message.id,
    event: message.event as LiveEventName,
    ids,
    occurredAt: typeof data.occurred_at === "number" ? data.occurred_at : 0,
  };
}

/** The heartbeat and lifetime `stream.ready` announces (defaults when missing). */
export function readStreamTimings(message: ServerSentEvent): StreamTimings {
  const data = readJson(message.data) ?? {};
  const number = (value: unknown, fallback: number) =>
    typeof value === "number" && value > 0 ? value : fallback;
  return { heartbeatSeconds: number(data.heartbeat_seconds, 20), lifetimeSeconds: number(data.lifetime_seconds, 900) };
}

/** Everything the cabinet shows about a business, for `stream.resync`. */
export function everythingOf(businessId: string): QueryKey[] {
  return [
    queryKeys.inbox.all(businessId),
    queryKeys.dashboard.all(businessId),
    queryKeys.conversations.all(businessId),
    queryKeys.handoffs.all(businessId),
    queryKeys.leads.all(businessId),
    queryKeys.bookings.all(businessId),
    queryKeys.channels.all(businessId),
    queryKeys.assistant.all(businessId),
  ];
}

const CONVERSATION_PREFIX = "conversation_";
const NOTE_PREFIX = "conversation_note_";

/** The conversations an event names (an assignment names the assignee too, a note itself). */
function conversationsIn(event: LiveEvent): string[] {
  return event.ids.filter((id) => id.startsWith(CONVERSATION_PREFIX) && !id.startsWith(NOTE_PREFIX));
}

/** The cached queries a change makes out of date (the counts always among them). */
export function invalidationsFor(event: LiveEvent, businessId: string): QueryKey[] {
  const counts = queryKeys.inbox.all(businessId);
  const dashboard = queryKeys.dashboard.all(businessId);
  switch (event.event) {
    case "handoff.created":
    case "handoff.resolved":
      return [counts, dashboard, queryKeys.handoffs.all(businessId), queryKeys.conversations.all(businessId)];
    case "conversation.message":
      return [
        dashboard,
        ["conversations", businessId, "list"],
        queryKeys.conversations.inboxAll(businessId),
        ...conversationsIn(event).map((conversationId) => queryKeys.conversations.detail(businessId, conversationId)),
      ];
    case "conversation.assigned":
      // The views (Mine, Unassigned), the rows and the cards that show who handles it.
      return [
        counts,
        queryKeys.conversations.inboxAll(businessId),
        ...conversationsIn(event).map((conversationId) => queryKeys.conversations.detail(businessId, conversationId)),
      ];
    case "conversation.note":
      // The notes of the conversation and the note counts on the rows.
      return [
        queryKeys.conversations.inboxAll(businessId),
        ...conversationsIn(event).map((conversationId) => queryKeys.conversations.notes(businessId, conversationId)),
      ];
    case "lead.created":
    case "lead.changed":
      // A request opens or closes: the Requests view and the cards it is on.
      return [counts, dashboard, queryKeys.leads.all(businessId), queryKeys.conversations.all(businessId)];
    case "booking.created":
    case "booking.changed":
      return [counts, dashboard, queryKeys.bookings.all(businessId)];
    case "channel.error":
    case "channel.changed":
      return [counts, queryKeys.channels.all(businessId)];
    case "autotest.progress":
      return [queryKeys.assistant.all(businessId)];
    case "knowledge_import.progress":
      // The import's progress, and its drafts among the knowledge items.
      return [queryKeys.knowledge.all(businessId)];
  }
}
