import { describe, expect, it } from "vitest";

import { everythingOf, invalidationsFor, readLiveEvent, readStreamTimings, type LiveEvent } from "./liveEvents";
import { queryKeys } from "./queryKeys";

const BUSINESS = "business_1";

function event(name: LiveEvent["event"], ids: string[] = []): LiveEvent {
  return { id: "1", event: name, ids, occurredAt: 0 };
}

describe("live events", () => {
  it("read the kind, ids and time of a known change", () => {
    expect(
      readLiveEvent({
        id: "017-ab",
        event: "handoff.created",
        data: '{"event":"handoff.created","ids":["handoff_1","conversation_2",3],"occurred_at":17}',
      }),
    ).toEqual({ id: "017-ab", event: "handoff.created", ids: ["handoff_1", "conversation_2"], occurredAt: 17 });
    expect(readLiveEvent({ id: null, event: "lead.created", data: "not json" })).toEqual({
      id: null,
      event: "lead.created",
      ids: [],
      occurredAt: 0,
    });
    expect(readLiveEvent({ id: null, event: "something.new", data: "{}" })).toBeNull();
  });

  it("read the stream's timings, with defaults", () => {
    expect(readStreamTimings({ id: null, event: "stream.ready", data: '{"heartbeat_seconds":5,"lifetime_seconds":60}' })).toEqual({
      heartbeatSeconds: 5,
      lifetimeSeconds: 60,
    });
    expect(readStreamTimings({ id: null, event: "stream.ready", data: "[]" })).toEqual({
      heartbeatSeconds: 20,
      lifetimeSeconds: 900,
    });
  });

  it("make the lists they touch and the counts out of date", () => {
    const counts = queryKeys.inbox.all(BUSINESS);
    expect(invalidationsFor(event("handoff.created"), BUSINESS)).toEqual([
      counts,
      queryKeys.dashboard.all(BUSINESS),
      queryKeys.handoffs.all(BUSINESS),
      queryKeys.conversations.all(BUSINESS),
    ]);
    expect(invalidationsFor(event("lead.changed"), BUSINESS)).toContainEqual(queryKeys.leads.all(BUSINESS));
    expect(invalidationsFor(event("booking.created"), BUSINESS)).toContainEqual(queryKeys.bookings.all(BUSINESS));
    expect(invalidationsFor(event("channel.error"), BUSINESS)).toEqual([counts, queryKeys.channels.all(BUSINESS)]);
    expect(invalidationsFor(event("autotest.progress"), BUSINESS)).toEqual([queryKeys.assistant.all(BUSINESS)]);
    expect(invalidationsFor(event("knowledge_import.progress"), BUSINESS)).toEqual([queryKeys.knowledge.all(BUSINESS)]);
  });

  it("reload only the conversation a message belongs to, never the counts", () => {
    const keys = invalidationsFor(event("conversation.message", ["conversation_9"]), BUSINESS);

    expect(keys).toContainEqual(["conversations", BUSINESS, "list"]);
    expect(keys).toContainEqual(queryKeys.conversations.inboxAll(BUSINESS));
    expect(keys).toContainEqual(queryKeys.conversations.detail(BUSINESS, "conversation_9"));
    expect(keys).not.toContainEqual(queryKeys.inbox.all(BUSINESS));
    expect(keys).not.toContainEqual(queryKeys.conversations.all(BUSINESS));
  });

  it("reload the views, rows and card of an assigned conversation, not the assignee", () => {
    const keys = invalidationsFor(event("conversation.assigned", ["conversation_9", "user_4"]), BUSINESS);

    expect(keys).toEqual([
      queryKeys.inbox.all(BUSINESS),
      queryKeys.conversations.inboxAll(BUSINESS),
      queryKeys.conversations.detail(BUSINESS, "conversation_9"),
    ]);
  });

  it("reload the notes of a conversation and the note counts, never the card", () => {
    const keys = invalidationsFor(event("conversation.note", ["conversation_9", "conversation_note_2"]), BUSINESS);

    expect(keys).toEqual([
      queryKeys.conversations.inboxAll(BUSINESS),
      queryKeys.conversations.notes(BUSINESS, "conversation_9"),
    ]);
  });

  it("reload the requests view when a request opens or closes", () => {
    expect(invalidationsFor(event("lead.created"), BUSINESS)).toContainEqual(queryKeys.conversations.all(BUSINESS));
  });

  it("reload everything of the business on a resync", () => {
    expect(everythingOf(BUSINESS)).toContainEqual(queryKeys.inbox.all(BUSINESS));
    expect(everythingOf(BUSINESS)).toHaveLength(8);
  });
});
