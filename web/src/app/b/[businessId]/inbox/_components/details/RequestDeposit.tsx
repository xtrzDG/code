"use client";

import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useBusiness } from "@/components/business/BusinessContext";
import { DepositPayment } from "@/components/deposits/DepositPayment";
import type { ConversationDetailView, LeadListItem } from "@/components/insights/types";

import { cardWithPaidRequestDeposit } from "../../_lib/cardUpdates";

/**
 * The deposit the assistant asked for a banquet request: the amount and
 * its state, until when the payment link is valid, and "Paid" once staff
 * see the money in their merchant account (the request keeps its status).
 */
export function RequestDeposit({ lead }: { lead: LeadListItem }) {
  const { business } = useBusiness();
  if (!lead.deposit) {
    return null;
  }
  const conversationId = lead.conversation_id ?? null;
  const showPaid = () => {
    if (conversationId) {
      queryCache.update<ConversationDetailView>(queryKeys.conversations.detail(business.id, conversationId), (card) =>
        cardWithPaidRequestDeposit(card, lead.id),
      );
    }
  };
  return (
    <DepositPayment
      deposit={lead.deposit}
      heldUntilKey="deposits.request.linkUntil"
      confirmKey="deposits.request.confirmDescription"
      onPaid={showPaid}
    />
  );
}
