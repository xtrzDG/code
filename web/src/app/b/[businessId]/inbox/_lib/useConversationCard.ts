"use client";

/**
 * One conversation as its card shows it: GET …/conversations/{id} (each
 * view is audited, so it never polls; the live stream reloads it when a
 * message arrives or it is reassigned), earlier messages page by page,
 * and the local changes after a staff message is sent.
 */

import { useCallback, useLayoutEffect, useRef, type RefObject } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import type { ConversationDetailView, MessagePage, MessageView } from "@/components/insights/types";

import { addUsage } from "./conversationUsage";
import { useEarlierMessages } from "./useEarlierMessages";

export function useConversationCard(conversationId: string) {
  const { business } = useBusiness();
  const detail = useQuery(queryKeys.conversations.detail(business.id, conversationId), () =>
    api.GET("/v1/businesses/{business_id}/conversations/{conversation_id}", {
      params: { path: { business_id: business.id, conversation_id: conversationId } },
    }),
  );
  const setDetail = detail.setData;
  const prependEarlier = useCallback(
    (page: MessagePage) =>
      setDetail((current) =>
        current
          ? {
              ...current,
              messages: [...(page.items ?? []), ...(current.messages ?? [])],
              earlier_messages_cursor: page.next_cursor ?? null,
            }
          : current,
      ),
    [setDetail],
  );
  const earlier = useEarlierMessages(conversationId, detail.data?.earlier_messages_cursor ?? null, prependEarlier);

  const addMessage = (message: MessageView) =>
    setDetail((current) =>
      current
        ? {
            ...current,
            messages: [...(current.messages ?? []), message],
            usage: current.usage ? addUsage(current.usage, message) : current.usage,
            conversation: {
              ...current.conversation,
              message_count: current.conversation.message_count + 1,
              last_message_at: Math.max(current.conversation.last_message_at, message.created_at),
            },
          }
        : current,
    );

  const card: ConversationDetailView | undefined =
    detail.data && detail.data.conversation.id === conversationId ? detail.data : undefined;
  return { card, detail, earlier, addMessage };
}

/** How close to the end (px) still counts as reading the newest messages. */
const NEAR_END_PX = 240;

/**
 * Keeps the newest messages in sight: on opening a conversation, and when
 * one more arrives while the person is at the end (not while they read
 * earlier ones). The transcript scrolls in its own area on large screens,
 * the page scrolls on phones.
 */
export function useScrollToLatest(area: RefObject<HTMLElement | null>, conversationId: string, messageCount: number) {
  const shown = useRef<{ id: string; count: number } | null>(null);
  useLayoutEffect(() => {
    const element = area.current;
    if (!element || messageCount === 0) {
      return;
    }
    const scrollsItself = element.scrollHeight > element.clientHeight + 1 && getComputedStyle(element).overflowY !== "visible";
    const isNewConversation = shown.current?.id !== conversationId;
    const grew = !isNewConversation && messageCount > (shown.current?.count ?? 0);
    shown.current = { id: conversationId, count: messageCount };
    if (!isNewConversation && !grew) {
      return;
    }
    if (scrollsItself) {
      const isNearEnd = element.scrollHeight - element.scrollTop - element.clientHeight < NEAR_END_PX;
      if (isNewConversation || isNearEnd) {
        element.scrollTo({ top: element.scrollHeight });
      }
      return;
    }
    const page = document.documentElement;
    const isNearEnd = page.scrollHeight - window.scrollY - window.innerHeight < NEAR_END_PX;
    if (isNewConversation || isNearEnd) {
      window.scrollTo({ top: page.scrollHeight });
    }
  }, [area, conversationId, messageCount]);
}
