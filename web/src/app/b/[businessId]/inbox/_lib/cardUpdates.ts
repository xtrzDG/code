/**
 * Pure changes of cached inbox data after an action on a conversation:
 * the new assignment on its card and on its rows, a resolved handoff, a
 * request's new status, a note more or less. The screens apply them at
 * once; the live stream brings the server's own copy right after.
 */

import type { PagedData } from "@/api/paging";
import type { ConversationDetailView, HandoffListItem, LeadStatus } from "@/components/insights/types";

import type { ConversationAssignmentView, InboxItemView, InboxPage } from "./types";

export type InboxListData = PagedData<InboxItemView, InboxPage>;

/** The card with another assignment. */
export function cardWithAssignment(
  card: ConversationDetailView,
  assignment: ConversationAssignmentView,
): ConversationDetailView {
  return card.conversation.id === assignment.conversation_id ? { ...card, assignment } : card;
}

/** The rows of a list with the conversation's new assignment. */
export function rowsWithAssignment(data: InboxListData, assignment: ConversationAssignmentView): InboxListData {
  if (!data.items.some((item) => item.id === assignment.conversation_id)) {
    return data;
  }
  return {
    ...data,
    items: data.items.map((item) =>
      item.id === assignment.conversation_id
        ? {
            ...item,
            assignee_user_id: assignment.assignee_user_id ?? null,
            assigned_at: assignment.assigned_at ?? null,
            is_assigned_automatically: assignment.is_assigned_automatically,
            assignment_revision: assignment.assignment_revision,
          }
        : item,
    ),
  };
}

/** The assignment a person asked for, shown until the server answers (same revision). */
export function requestedAssignment(
  current: ConversationAssignmentView,
  assigneeUserId: string | null,
  byUserId: string,
  nowMicros: number,
): ConversationAssignmentView {
  return {
    ...current,
    assignee_user_id: assigneeUserId,
    assigned_by: assigneeUserId ? byUserId : null,
    assigned_at: assigneeUserId ? nowMicros : null,
    is_assigned_automatically: false,
  };
}

/** The card after a handoff was resolved: the handoff replaced; no open one left, the assistant answers again. */
export function cardWithResolvedHandoff(card: ConversationDetailView, resolved: HandoffListItem): ConversationDetailView {
  const handoffs = (card.handoffs ?? []).map((handoff) => (handoff.id === resolved.id ? resolved : handoff));
  const stillOpen = handoffs.some((handoff) => handoff.status !== "resolved");
  return {
    ...card,
    handoffs,
    conversation:
      !stillOpen && card.conversation.status === "handoff"
        ? { ...card.conversation, status: "open" }
        : card.conversation,
  };
}

/** The card with one request in another status. */
export function cardWithRequestStatus(card: ConversationDetailView, leadId: string, status: LeadStatus): ConversationDetailView {
  return {
    ...card,
    leads: (card.leads ?? []).map((lead) => (lead.id === leadId ? { ...lead, status } : lead)),
  };
}

/** The rows of a list with one note more (+1) or less (-1) on a conversation. */
export function rowsWithNoteDelta(data: InboxListData, conversationId: string, delta: number): InboxListData {
  if (!data.items.some((item) => item.id === conversationId)) {
    return data;
  }
  return {
    ...data,
    items: data.items.map((item) =>
      item.id === conversationId ? { ...item, note_count: Math.max(0, item.note_count + delta) } : item,
    ),
  };
}

/** The handoff of the card that still waits for a person (the newest one), if any. */
export function openHandoffOf(card: ConversationDetailView): HandoffListItem | null {
  const open = (card.handoffs ?? []).filter((handoff) => handoff.status !== "resolved");
  return open.sort((left, right) => right.created_at - left.created_at)[0] ?? null;
}

/** The requests of the card that are still open (new or in progress), newest first. */
export function openRequestsOf(card: ConversationDetailView) {
  return (card.leads ?? [])
    .filter((lead) => lead.status === "new" || lead.status === "in_progress")
    .sort((left, right) => right.created_at - left.created_at);
}
