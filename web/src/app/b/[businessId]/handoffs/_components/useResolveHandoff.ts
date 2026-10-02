"use client";

import { api } from "@/api/client";
import type { PagedData } from "@/api/paging";
import { queryCache, type QueryKey } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import type { HandoffListItem, HandoffPage } from "@/components/insights/types";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { resolvedLocally, withResolvedHandoff, type HandoffTab } from "./handoffModel";

type HandoffList = PagedData<HandoffListItem, HandoffPage>;

/**
 * Resolving a handoff after the confirmation: the dialog closes and the
 * handoff leaves the open list at once; if the API refuses, it comes back
 * (with the error) and the dialog opens again. There is no way to reopen a
 * handoff, so no Undo is offered.
 */
export function useResolveHandoff(
  listKey: QueryKey,
  tab: HandoffTab,
  setResolving: (handoff: HandoffListItem | null) => void,
) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();

  const mutation = useMutation(
    (handoff: HandoffListItem) =>
      api.POST("/v1/businesses/{business_id}/handoffs/{handoff_id}/resolve", {
        params: { path: { business_id: business.id, handoff_id: handoff.id } },
      }),
    {
      optimistic: (handoff) =>
        queryCache.update<HandoffList>(listKey, (data) =>
          withResolvedHandoff(data, resolvedLocally(handoff, Date.now() * 1000), tab),
        ),
      rollback: (_error, handoff) => setResolving(handoff),
      // The shown list has the change; other tabs, the dashboard count and the
      // conversation's card load again when shown.
      stale: [queryKeys.handoffs.all(business.id), queryKeys.conversations.all(business.id)],
      invalidate: [queryKeys.dashboard.all(business.id)],
    },
  );

  const run = async (handoff: HandoffListItem) => {
    setResolving(null);
    const result = await mutation.run(handoff);
    if (result.ok) {
      // The server's own copy (resolved time, status) replaces the local one.
      queryCache.update<HandoffList>(listKey, (data) => ({
        ...data,
        items: data.items.map((item) => (item.id === result.data.id ? result.data : item)),
      }));
      toast.success(t("handoffs.resolved"));
    }
  };

  return { run, isPending: mutation.isPending };
}
