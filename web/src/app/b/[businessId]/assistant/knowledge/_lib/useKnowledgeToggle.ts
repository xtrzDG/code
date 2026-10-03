"use client";

import { api } from "@/api/client";
import type { PagedData } from "@/api/paging";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import type { KnowledgeItemDetails, KnowledgeItemKind, Schema } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { withSavedItem, type KnowledgeStatusFilter } from "@/lib/knowledge/kinds";

type ItemList = PagedData<KnowledgeItemDetails, Schema<"KnowledgeItemPage">>;

/** Every cached items list (each filter) with one item saved into it. */
function saveIntoLists(businessId: string, saved: KnowledgeItemDetails) {
  return queryCache.update<ItemList>([...queryKeys.knowledge.all(businessId), "items"], (data, key) => ({
    ...data,
    // The key ends with the list's filter: …, kind, status.
    items: withSavedItem(data.items, saved, {
      kind: key[4] as KnowledgeItemKind | "all",
      status: key[5] as KnowledgeStatusFilter,
    }),
  }));
}

/**
 * Switching an item on or off: the switch and the lists move at once (an
 * item switched off leaves the "active" list) and go back if the API
 * refuses. The switch itself undoes it, so no Undo toast.
 */
export function useKnowledgeToggle() {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();

  const mutation = useMutation(
    (item: KnowledgeItemDetails, isActive: boolean) =>
      api.PATCH("/v1/businesses/{business_id}/knowledge/{item_id}", {
        params: { path: { business_id: business.id, item_id: item.id }, query: { language: locale } },
        body: { is_active: isActive },
      }),
    {
      optimistic: (item, isActive) => saveIntoLists(business.id, { ...item, is_active: isActive }),
      // The profile's gaps and the assistant's go-live checks count the items.
      stale: [queryKeys.profile.all(business.id), queryKeys.assistant.all(business.id)],
      invalidate: [queryKeys.assistant.pendingAll(business.id)],
    },
  );

  const setActive = async (item: KnowledgeItemDetails, isActive: boolean) => {
    const result = await mutation.run(item, isActive);
    if (result.ok) {
      saveIntoLists(business.id, result.data);
      toast.success(
        isActive
          ? t("knowledge.items.switchedOn", { title: item.title })
          : t("knowledge.items.switchedOff", { title: item.title }),
      );
    }
  };

  return { setActive, saveIntoLists: (saved: KnowledgeItemDetails) => saveIntoLists(business.id, saved) };
}
