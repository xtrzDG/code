"use client";

/**
 * The quick-reply picker of the reply box: it opens when the text is "/"
 * followed by a word (or from its button), lists the business's quick
 * replies filled in for this conversation (GET …/quick-replies: its
 * language, the customer's name and booking; loaded on first use, audited
 * as a view of the customer), filters them by what follows "/", and
 * moves with the arrow keys.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

import { matchQuickReplies, slashQuery } from "./quickReplyMatching";

export function useQuickReplyPicker(conversationId: string, draft: string) {
  const { business } = useBusiness();
  // Opened from the button with nothing typed after "/".
  const [isForced, setForced] = useState(false);
  const [isDismissed, setDismissed] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const query = slashQuery(draft);
  const isOpen = !isDismissed && (isForced || query !== null);

  const replies = useQuery(
    queryKeys.conversations.quickReplies(business.id, conversationId),
    () =>
      api.GET("/v1/businesses/{business_id}/conversations/{conversation_id}/quick-replies", {
        params: { path: { business_id: business.id, conversation_id: conversationId } },
      }),
    { enabled: isOpen, staleMs: 60_000 },
  );
  const matches = matchQuickReplies(replies.data?.items ?? [], query ?? "");
  const active = matches.length > 0 ? matches[Math.min(activeIndex, matches.length - 1)] : undefined;

  return {
    isOpen,
    query: query ?? "",
    replies,
    matches,
    active: active ?? null,
    activeIndex: Math.min(activeIndex, Math.max(0, matches.length - 1)),
    open: () => {
      setDismissed(false);
      setForced(true);
      setActiveIndex(0);
    },
    close: () => {
      setForced(false);
      setDismissed(true);
    },
    /** The text changed: a new "/" opens the picker again. */
    onDraft: (next: string) => {
      setActiveIndex(0);
      if (slashQuery(next) === null) {
        setDismissed(false);
        setForced(false);
      }
    },
    move: (step: 1 | -1) =>
      setActiveIndex((index) => (matches.length === 0 ? 0 : (index + step + matches.length) % matches.length)),
    setActiveIndex,
  };
}

export type QuickReplyPicker = ReturnType<typeof useQuickReplyPicker>;
