"use client";

/**
 * Teaching the assistant over the API: the draft of "Fix this answer" and
 * the correction, the owner's checks, and the Overview's answers worth
 * improving. A correction joins the changes not with customers yet, so the
 * pending changes and the knowledge lists load again after it.
 */

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import type { CheckBody, CheckChanges, CheckView, CorrectionBody } from "@/lib/teaching";

type CheckList = { items?: CheckView[]; limit: number };

/** How many answers worth improving the Overview shows. */
const IMPROVE_LIST_SIZE = 5;

/** The Overview's list: a few answers, owners and staff alike. */
export function useAnswersToImprove(enabled = true) {
  const { business } = useBusiness();
  return useQuery(
    queryKeys.dashboard.answersToImprove(business.id),
    () =>
      api.GET("/v1/businesses/{business_id}/answers-to-improve", {
        params: { path: { business_id: business.id }, query: { limit: String(IMPROVE_LIST_SIZE) } },
      }),
    { enabled },
  );
}

/** The draft of "Fix this answer" for one assistant answer, loaded when the dialog opens. */
export function useCorrectionDraft(conversationId: string, messageId: string | null) {
  const { business } = useBusiness();
  return useQuery(
    queryKeys.conversations.correction(business.id, conversationId, messageId ?? ""),
    () =>
      api.GET("/v1/businesses/{business_id}/conversations/{conversation_id}/messages/{message_id}/correction", {
        params: { path: { business_id: business.id, conversation_id: conversationId, message_id: messageId ?? "" } },
      }),
    // Each read is audited: load it when the dialog asks, and again only when reopened.
    { enabled: messageId !== null, staleMs: 0 },
  );
}

/** Saves a correction; the changes not with customers yet and the knowledge reload. */
export function useCorrectAnswer(conversationId: string) {
  const { business } = useBusiness();
  return useMutation(
    (messageId: string, body: CorrectionBody) =>
      api.POST("/v1/businesses/{business_id}/conversations/{conversation_id}/messages/{message_id}/correction", {
        params: { path: { business_id: business.id, conversation_id: conversationId, message_id: messageId } },
        body,
      }),
    {
      errorToast: false,
      invalidate: [queryKeys.assistant.pendingAll(business.id), queryKeys.dashboard.answersToImprove(business.id)],
      stale: [queryKeys.knowledge.all(business.id)],
    },
  );
}

/** "My checks": the list, and adding, changing and deleting one. */
export function useChecks(enabled = true) {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const listKey = queryKeys.assistant.checks(business.id);
  const list = useQuery(listKey, () => api.GET("/v1/businesses/{business_id}/autotest-cases", { params: { path } }), {
    enabled,
  });

  const create = useMutation(
    (body: CheckBody) => api.POST("/v1/businesses/{business_id}/autotest-cases", { params: { path }, body }),
    { errorToast: false, invalidate: [listKey, queryKeys.dashboard.answersToImprove(business.id)] },
  );

  const update = useMutation(
    (checkId: string, changes: CheckChanges) =>
      api.PATCH("/v1/businesses/{business_id}/autotest-cases/{case_id}", {
        params: { path: { ...path, case_id: checkId } },
        body: changes,
      }),
    { errorToast: false },
  );

  const remove = useMutation(
    (check: CheckView) =>
      api.DELETE("/v1/businesses/{business_id}/autotest-cases/{case_id}", {
        params: { path: { ...path, case_id: check.id } },
      }),
    {
      optimistic: (check) =>
        queryCache.update<CheckList>(listKey, (data) => ({
          ...data,
          items: (data.items ?? []).filter((item) => item.id !== check.id),
        })),
    },
  );

  /** Puts a changed check in the list at once. */
  const replace = (saved: CheckView) =>
    queryCache.update<CheckList>(listKey, (data) => ({
      ...data,
      items: (data.items ?? []).map((item) => (item.id === saved.id ? saved : item)),
    }));

  return { list, create, update, remove, replace };
}
