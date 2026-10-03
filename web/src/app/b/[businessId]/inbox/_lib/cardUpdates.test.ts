import { describe, expect, it } from "vitest";

import type { ConversationDetailView, HandoffListItem, LeadListItem } from "@/components/insights/types";

import {
  cardWithAssignment,
  cardWithRequestStatus,
  cardWithResolvedHandoff,
  openHandoffOf,
  openRequestsOf,
  requestedAssignment,
  rowsWithAssignment,
  rowsWithNoteDelta,
  type InboxListData,
} from "./cardUpdates";
import type { ConversationAssignmentView, InboxItemView } from "./types";

const handoff = (id: string, status: string, createdAt: number) =>
  ({ id, status, created_at: createdAt }) as unknown as HandoffListItem;
const lead = (id: string, status: string, createdAt: number) => ({ id, status, created_at: createdAt }) as unknown as LeadListItem;

function cardOf(overrides: Partial<ConversationDetailView> = {}): ConversationDetailView {
  return {
    conversation: { id: "conversation_1", status: "handoff" },
    handoffs: [],
    leads: [],
    ...overrides,
  } as unknown as ConversationDetailView;
}

const assignment: ConversationAssignmentView = {
  conversation_id: "conversation_1",
  assignee_user_id: "user_2",
  assigned_at: 50,
  assigned_by: "user_1",
  assignment_revision: 4,
  is_assigned_automatically: false,
};

function listOf(...items: Partial<InboxItemView>[]): InboxListData {
  return { items: items as InboxItemView[], page: undefined } as unknown as InboxListData;
}

describe("an assignment", () => {
  it("lands on its own card and leaves another one as it was", () => {
    expect(cardWithAssignment(cardOf(), assignment).assignment).toEqual(assignment);
    const other = cardOf({ conversation: { id: "conversation_9" } as ConversationDetailView["conversation"] });
    expect(cardWithAssignment(other, assignment)).toBe(other);
  });

  it("moves to the conversation's rows with its revision", () => {
    const data = listOf(
      { id: "conversation_1", assignee_user_id: null, assignment_revision: 3, note_count: 0 },
      { id: "conversation_2", assignee_user_id: null, assignment_revision: 1, note_count: 0 },
    );
    const next = rowsWithAssignment(data, assignment);
    expect(next.items[0]).toMatchObject({ assignee_user_id: "user_2", assignment_revision: 4, assigned_at: 50 });
    expect(next.items[1]).toBe(data.items[1]);
    expect(rowsWithAssignment(listOf({ id: "conversation_7" }), assignment).items[0]).toMatchObject({ id: "conversation_7" });
  });

  it("asked for shows at once with the revision the person saw", () => {
    const current = { ...assignment, assignee_user_id: null, assigned_by: null, assigned_at: null, assignment_revision: 3 };
    expect(requestedAssignment(current, "user_5", "user_1", 99)).toMatchObject({
      assignee_user_id: "user_5",
      assigned_by: "user_1",
      assigned_at: 99,
      assignment_revision: 3,
      is_assigned_automatically: false,
    });
    expect(requestedAssignment(assignment, null, "user_1", 99)).toMatchObject({ assignee_user_id: null, assigned_by: null });
  });
});

describe("a resolved handoff", () => {
  it("gives the conversation back to the assistant when no other handoff is open", () => {
    const card = cardOf({ handoffs: [handoff("handoff_1", "notified", 1)] });
    const next = cardWithResolvedHandoff(card, handoff("handoff_1", "resolved", 1));
    expect(next.conversation.status).toBe("open");
    expect(openHandoffOf(next)).toBeNull();
  });

  it("keeps the conversation with a person while another handoff waits", () => {
    const card = cardOf({ handoffs: [handoff("handoff_1", "notified", 1), handoff("handoff_2", "notified", 2)] });
    const next = cardWithResolvedHandoff(card, handoff("handoff_1", "resolved", 1));
    expect(next.conversation.status).toBe("handoff");
    expect(openHandoffOf(next)?.id).toBe("handoff_2");
  });
});

describe("requests and notes", () => {
  it("lists open requests newest first and moves one to another status", () => {
    const card = cardOf({ leads: [lead("lead_1", "new", 1), lead("lead_2", "won", 2), lead("lead_3", "in_progress", 3)] });
    expect(openRequestsOf(card).map((item) => item.id)).toEqual(["lead_3", "lead_1"]);
    expect(openRequestsOf(cardWithRequestStatus(card, "lead_1", "lost")).map((item) => item.id)).toEqual(["lead_3"]);
  });

  it("counts a note more or less on the conversation's row, never below zero", () => {
    const data = listOf({ id: "conversation_1", note_count: 1 }, { id: "conversation_2", note_count: 0 });
    expect(rowsWithNoteDelta(data, "conversation_1", 1).items[0]?.note_count).toBe(2);
    expect(rowsWithNoteDelta(data, "conversation_2", -1).items[1]?.note_count).toBe(0);
    expect(rowsWithNoteDelta(data, "conversation_9", 1)).toBe(data);
  });
});
