"use client";

/**
 * The actions on the work of a conversation, from its card: resolving the
 * handoff (the assistant answers the customer again; there is no way back,
 * so no Undo) and moving a request to another status (with Undo). The card
 * changes at once and goes back if the API refuses; the inbox's counts and
 * the dashboard load again.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { LEAD_STATUS } from "@/components/insights/labels";
import type { ConversationDetailView, HandoffListItem, LeadListItem, LeadStatus } from "@/components/insights/types";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { cardWithRequestStatus, cardWithResolvedHandoff } from "./cardUpdates";

export function useResolveHandoff(conversationId: string) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const detailKey = queryKeys.conversations.detail(business.id, conversationId);

  const mutation = useMutation(
    (handoff: HandoffListItem) =>
      api.POST("/v1/businesses/{business_id}/handoffs/{handoff_id}/resolve", {
        params: { path: { business_id: business.id, handoff_id: handoff.id } },
      }),
    {
      optimistic: (handoff) =>
        queryCache.update<ConversationDetailView>(detailKey, (card) =>
          cardWithResolvedHandoff(card, { ...handoff, status: "resolved", resolved_at: Date.now() * 1000 }),
        ),
      // The card shows the change; the lists, counts and dashboard follow.
      invalidate: [
        queryKeys.inbox.all(business.id),
        queryKeys.dashboard.all(business.id),
        queryKeys.conversations.inboxAll(business.id),
      ],
      stale: [queryKeys.handoffs.all(business.id)],
    },
  );

  const resolve = async (handoff: HandoffListItem) => {
    const result = await mutation.run(handoff);
    if (result.ok) {
      queryCache.update<ConversationDetailView>(detailKey, (card) => cardWithResolvedHandoff(card, result.data));
      toast.success(t("inboxCard.resolved"));
    }
    return result.ok;
  };

  return { resolve, isPending: mutation.isPending };
}

export function useRequestStatus(conversationId: string) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const detailKey = queryKeys.conversations.detail(business.id, conversationId);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const mutation = useMutation(
    (lead: LeadListItem, status: LeadStatus) =>
      api.PATCH("/v1/businesses/{business_id}/leads/{lead_id}", {
        params: { path: { business_id: business.id, lead_id: lead.id } },
        body: { status },
      }),
    {
      optimistic: (lead, status) =>
        queryCache.update<ConversationDetailView>(detailKey, (card) => cardWithRequestStatus(card, lead.id, status)),
      invalidate: [
        queryKeys.inbox.all(business.id),
        queryKeys.dashboard.all(business.id),
        queryKeys.conversations.inboxAll(business.id),
      ],
      stale: [queryKeys.leads.all(business.id)],
    },
  );

  const run = async (lead: LeadListItem, status: LeadStatus) => {
    setPendingId(lead.id);
    const result = await mutation.run(lead, status);
    setPendingId(null);
    return result.ok;
  };

  const change = async (lead: LeadListItem, status: LeadStatus) => {
    if (status === lead.status || !(await run(lead, status))) {
      return;
    }
    toast.undoable(t("inboxCard.request.updated", { status: t(LEAD_STATUS[status].label) }), () => {
      void run({ ...lead, status }, lead.status).then((isDone) => {
        if (isDone) {
          toast.success(t("inboxCard.request.updated", { status: t(LEAD_STATUS[lead.status].label) }));
        }
      });
    });
  };

  return { change, isPending: (leadId: string) => pendingId === leadId };
}
