"use client";

import { useCallback, useState } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import { useBusiness } from "@/components/business/BusinessContext";
import type { MessagePage } from "@/components/insights/types";

/** How many earlier messages one click loads. */
export const EARLIER_PAGE_SIZE = 100;

export interface EarlierMessages {
  hasMore: boolean;
  isLoading: boolean;
  error: unknown;
  load: () => void;
}

/**
 * The card shows the newest messages of a long conversation; this loads
 * the ones before them, page by page, and hands each page to `onLoaded`
 * (which puts it above the shown ones). Every page read is audited.
 */
export function useEarlierMessages(
  conversationId: string,
  cursor: string | null,
  onLoaded: (page: MessagePage) => void,
): EarlierMessages {
  const { business } = useBusiness();
  const [state, setState] = useState<{ isLoading: boolean; error: unknown }>({ isLoading: false, error: null });

  const load = useCallback(() => {
    if (!cursor || state.isLoading) {
      return;
    }
    setState({ isLoading: true, error: null });
    unwrap(
      api.GET("/v1/businesses/{business_id}/conversations/{conversation_id}/messages", {
        params: {
          path: { business_id: business.id, conversation_id: conversationId },
          query: { cursor, limit: String(EARLIER_PAGE_SIZE) },
        },
      }),
    ).then(
      (page) => {
        onLoaded(page);
        setState({ isLoading: false, error: null });
      },
      (error: unknown) => setState({ isLoading: false, error }),
    );
  }, [business.id, conversationId, cursor, onLoaded, state.isLoading]);

  return { hasMore: cursor !== null, isLoading: state.isLoading, error: state.error, load };
}
