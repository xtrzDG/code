"use client";

/**
 * Settings → Quick replies (owners): the business's quick replies, and
 * creating, replacing and deleting one. The list changes at once; the
 * replies filled in for open conversations load again when next used.
 */

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import type { QuickReplyBody, QuickReplyView } from "@/lib/quickReplies";

type ReplyList = { items?: QuickReplyView[] };

/** The replies filled in for each conversation: out of date after any change. */
const filledRepliesOf = (businessId: string) => [...queryKeys.conversations.all(businessId), "quickReplies"] as const;

export const QUICK_REPLY_REASONS = {
  shortcut_taken: () => ({ key: "quickReplies.errors.shortcut_taken" as const }),
  too_many_quick_replies: () => ({ key: "quickReplies.errors.too_many_quick_replies" as const }),
  unknown_variable: () => ({ key: "quickReplies.errors.unknown_variable" as const }),
  duplicate_language: () => ({ key: "quickReplies.errors.duplicate_language" as const }),
};

export function useQuickReplies() {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const listKey = queryKeys.quickReplies.list(business.id);
  const list = useQuery(listKey, () => api.GET("/v1/businesses/{business_id}/quick-replies", { params: { path } }));

  const save = useMutation(
    (body: QuickReplyBody, replyId: string | null) =>
      replyId
        ? api.PUT("/v1/businesses/{business_id}/quick-replies/{quick_reply_id}", {
            params: { path: { ...path, quick_reply_id: replyId } },
            body,
          })
        : api.POST("/v1/businesses/{business_id}/quick-replies", { params: { path }, body }),
    { errorToast: false, stale: [filledRepliesOf(business.id)] },
  );

  const remove = useMutation(
    (reply: QuickReplyView) =>
      api.DELETE("/v1/businesses/{business_id}/quick-replies/{quick_reply_id}", {
        params: { path: { ...path, quick_reply_id: reply.id } },
      }),
    {
      optimistic: (reply) =>
        queryCache.update<ReplyList>(listKey, (data) => ({
          ...data,
          items: (data.items ?? []).filter((item) => item.id !== reply.id),
        })),
      stale: [filledRepliesOf(business.id)],
    },
  );

  /** Saves the draft; the stored reply on success. */
  const saveReply = async (body: QuickReplyBody, replyId: string | null) => {
    const result = await save.run(body, replyId);
    if (result.ok) {
      const saved = result.data;
      queryCache.update<ReplyList>(listKey, (data) => {
        const items = data.items ?? [];
        return {
          ...data,
          items: items.some((item) => item.id === saved.id)
            ? items.map((item) => (item.id === saved.id ? saved : item))
            : [...items, saved],
        };
      });
    }
    return result;
  };

  return { list, saveReply, isSaving: save.isPending, deleteReply: remove.run };
}
