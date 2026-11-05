"use client";

/**
 * "Suggest translations" in the knowledge editor: the model names a stored
 * item in the business's other languages (POST …/aliases/suggest), and
 * what it stored comes back. The stored names become the editor's starting
 * point, and the suggestions join the form only in languages the form has
 * no name in yet, so the owner's unsaved names stay and saving sends only
 * the owner's own changes.
 */

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import {
  aliasesInLanguages,
  aliasRowsFrom,
  countSuggested,
  mergeSuggestions,
  type AliasRow,
} from "@/lib/knowledge/aliases";

import type { AliasSuggestAction } from "./AliasChips";

export function useAliasSuggestions({
  itemId,
  titleChanged,
  current,
  onStored,
}: {
  /** The stored item; null while it is being created (nothing to suggest for yet). */
  itemId: string | null;
  /** The title has unsaved changes: suggestions would translate the old one. */
  titleChanged: boolean;
  current: readonly AliasRow[];
  /** The stored names, and the form's names with the new suggestions joined. */
  onStored: (stored: AliasRow[], merged: AliasRow[]) => void;
}): AliasSuggestAction | undefined {
  const { t, tp, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const suggest = useMutation(
    (id: string) =>
      api.POST("/v1/businesses/{business_id}/knowledge/{item_id}/aliases/suggest", {
        params: {
          path: { business_id: business.id, item_id: id },
          query: { language: locale },
        },
      }),
    // The lists show the stored item: read again when next opened.
    { stale: [queryKeys.knowledge.all(business.id)] },
  );

  if (itemId === null) {
    return undefined;
  }

  const onSuggest = async () => {
    const result = await suggest.run(itemId);
    if (!result.ok) {
      return;
    }
    const stored = aliasesInLanguages(aliasRowsFrom(result.data.aliases), business.languages);
    const merged = mergeSuggestions(current, stored);
    const added = countSuggested(merged) - countSuggested(current);
    onStored(stored, merged);
    if (added > 0) {
      toast.success(tp("knowledge.aliases.suggestedCount", added));
    } else {
      toast.info(t("knowledge.aliases.nothingSuggested"));
    }
  };

  return {
    onSuggest: () => void onSuggest(),
    isPending: suggest.isPending,
    blockedReason: titleChanged ? t("knowledge.aliases.saveTitleFirst") : null,
  };
}
