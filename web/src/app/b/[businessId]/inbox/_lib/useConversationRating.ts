"use client";

import { api } from "@/api/client";
import type { PagedData } from "@/api/paging";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import type {
  ConversationDetailView,
  ConversationPage,
  ConversationRating,
  ConversationSummaryView,
} from "@/components/insights/types";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { RatingReason } from "@/lib/teaching";

type Feed = PagedData<ConversationSummaryView, ConversationPage>;

/** The feed rows and the card of one conversation with another rating (and why it was bad). */
function withRating(conversationId: string, rating: ConversationRating | null, reason: RatingReason | null) {
  const rate = <T extends ConversationSummaryView>(conversation: T): T =>
    conversation.id === conversationId ? { ...conversation, rating, rating_reason: reason } : conversation;
  return {
    feed: (data: Feed): Feed => ({ ...data, items: data.items.map(rate) }),
    card: (data: ConversationDetailView): ConversationDetailView => ({ ...data, conversation: rate(data.conversation) }),
  };
}

/**
 * Good / bad for a conversation, and for a bad one what was wrong: the
 * card and the feed show it at once and go back if the API refuses.
 * Rating again changes it, so no Undo.
 */
export function useConversationRating(conversationId: string) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const detailKey = queryKeys.conversations.detail(business.id, conversationId);

  const mutation = useMutation(
    (rating: ConversationRating | null, reason: RatingReason | null) =>
      api.PUT("/v1/businesses/{business_id}/conversations/{conversation_id}/rating", {
        params: { path: { business_id: business.id, conversation_id: conversationId } },
        body: { rating, reason },
      }),
    {
      optimistic: (rating, reason) => {
        const change = withRating(conversationId, rating, reason);
        const undoCard = queryCache.update<ConversationDetailView>(detailKey, change.card);
        const undoFeed = queryCache.update<Feed>([...queryKeys.conversations.all(business.id), "list"], change.feed);
        return () => {
          undoCard();
          undoFeed();
        };
      },
      invalidate: [queryKeys.dashboard.all(business.id)],
    },
  );

  const change = async (rating: ConversationRating | null, reason: RatingReason | null = null) => {
    const result = await mutation.run(rating, reason);
    if (result.ok) {
      queryCache.update<ConversationDetailView>(detailKey, (data) => ({ ...data, conversation: result.data }));
      toast.success(
        t(reason !== null ? "teaching.rating.reasonSaved" : rating === null ? "conversations.rating.cleared" : "conversations.rating.saved"),
      );
    }
  };

  return { change, isPending: mutation.isPending };
}
