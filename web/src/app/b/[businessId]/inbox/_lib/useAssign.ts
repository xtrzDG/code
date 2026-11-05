"use client";

/**
 * Assigning a conversation from its card (compare and set): the card and
 * the rows show the new person at once. If someone changed the assignment
 * meanwhile (409 `assignment_changed`), the change is undone, a toast says
 * so, and the card and the list load again to show how it stands now.
 */

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import type { ConversationDetailView } from "@/components/insights/types";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { cardWithAssignment, requestedAssignment, rowsWithAssignment, type InboxListData } from "./cardUpdates";
import type { TeamMember } from "./team";
import type { ConversationAssignmentView } from "./types";

const ASSIGNMENT_CHANGED = "assignment_changed";

function isAssignmentConflict(error: ApiError): boolean {
  return error.status === 409 || error.reasons.some((reason) => reason.code === ASSIGNMENT_CHANGED);
}

export function useAssign(conversationId: string) {
  const { t } = useI18n();
  const toast = useToast();
  const { business, me } = useBusiness();
  const detailKey = queryKeys.conversations.detail(business.id, conversationId);

  const mutation = useMutation(
    (current: ConversationAssignmentView, assignee: TeamMember | null) =>
      api.POST("/v1/businesses/{business_id}/conversations/{conversation_id}/assign", {
        params: { path: { business_id: business.id, conversation_id: conversationId } },
        body: { assignee_user_id: assignee?.userId ?? null, expected_revision: current.assignment_revision },
      }),
    {
      optimistic: (current, assignee) => {
        const shown = requestedAssignment(current, assignee?.userId ?? null, me.user.id, Date.now() * 1000);
        const undoCard = queryCache.update<ConversationDetailView>(detailKey, (card) => cardWithAssignment(card, shown));
        const undoRows = queryCache.update<InboxListData>(queryKeys.conversations.inboxAll(business.id), (data) =>
          rowsWithAssignment(data, shown),
        );
        return () => {
          undoCard();
          undoRows();
        };
      },
      rollback: (error) => {
        if (isAssignmentConflict(error)) {
          // How it stands now: the card, the rows, the counts.
          queryCache.invalidate(detailKey);
          queryCache.invalidate(queryKeys.conversations.inboxAll(business.id));
        }
      },
      // The views' counts and everyone's workload; the rows reload with the live event.
      invalidate: [queryKeys.inbox.all(business.id)],
      stale: [queryKeys.conversations.inboxAll(business.id)],
      reasonMessages: {
        [ASSIGNMENT_CHANGED]: () => ({ key: "inbox.assign.conflict" }),
        assigned_to_colleague: () => ({ key: "inbox.assign.colleague" }),
        not_a_member: () => ({ key: "inbox.assign.notMember" }),
      },
      errorMessages: { conflict: "inbox.assign.conflict" },
    },
  );

  const assign = async (current: ConversationAssignmentView, assignee: TeamMember | null) => {
    if ((current.assignee_user_id ?? null) === (assignee?.userId ?? null)) {
      return;
    }
    const result = await mutation.run(current, assignee);
    if (!result.ok) {
      return;
    }
    queryCache.update<ConversationDetailView>(detailKey, (card) => cardWithAssignment(card, result.data));
    queryCache.update<InboxListData>(queryKeys.conversations.inboxAll(business.id), (data) =>
      rowsWithAssignment(data, result.data),
    );
    toast.success(
      assignee === null
        ? t("inbox.assign.cleared")
        : assignee.isMe
          ? t("inbox.assign.taken")
          : assignee.name
            ? { text: t("inbox.assign.assigned"), values: { name: assignee.name } }
            : t("inbox.assign.assigned", { name: t("inbox.assign.teammate") }),
    );
  };

  return { assign, isPending: mutation.isPending };
}
