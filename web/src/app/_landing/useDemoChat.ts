"use client";

import { useCallback, useRef, useState } from "react";

import { api } from "@/api/client";
import { toApiError } from "@/api/errors";
import { unwrap } from "@/api/result";
import {
  cleanDemoMessage,
  demoFailure,
  newSessionKey,
  replyOutcomes,
  type DemoEntry,
  type DemoFailure,
} from "@/lib/publicSite/demoChat";

export interface DemoChatState {
  entries: DemoEntry[];
  isSending: boolean;
  failure: DemoFailure | null;
  messagesLeft: number;
  send: (text: string) => Promise<void>;
  restart: () => void;
}

/**
 * One visitor's conversation with one demo business (the chat is mounted
 * again for another demo): a fresh conversation key per conversation, the
 * transcript, what went wrong with the last send and the messages left
 * this hour. "Start over" forgets the key, so the next message opens a new
 * conversation; an answer to the forgotten one is dropped.
 */
export function useDemoChat(businessId: string, messagesPerHour: number): DemoChatState {
  const [entries, setEntries] = useState<DemoEntry[]>([]);
  const [isSending, setSending] = useState(false);
  const [failure, setFailure] = useState<DemoFailure | null>(null);
  const [messagesLeft, setMessagesLeft] = useState(messagesPerHour);
  const sessionKey = useRef<string | null>(null);
  const nextId = useRef(1);

  const restart = useCallback(() => {
    sessionKey.current = null;
    setEntries([]);
    setFailure(null);
    setSending(false);
  }, []);

  const send = useCallback(
    async (text: string) => {
      const message = cleanDemoMessage(text);
      if (message === null || isSending) {
        return;
      }
      sessionKey.current ??= newSessionKey();
      const key = sessionKey.current;
      setEntries((current) => [...current, { id: nextId.current++, role: "visitor", text: message }]);
      setFailure(null);
      setSending(true);
      try {
        const reply = await unwrap(
          api.POST("/v1/public-demos/{business_id}/messages", {
            params: { path: { business_id: businessId } },
            body: { text: message, session_key: key },
          }),
        );
        if (sessionKey.current !== key) {
          return;
        }
        setMessagesLeft(reply.messages_left);
        const answer = reply.text;
        if (answer) {
          setEntries((current) => [
            ...current,
            { id: nextId.current++, role: "assistant", text: answer, lang: reply.language, outcomes: replyOutcomes(reply) },
          ]);
        }
      } catch (error) {
        if (sessionKey.current === key) {
          setFailure(demoFailure(toApiError(error).code));
        }
      } finally {
        if (sessionKey.current === key) {
          setSending(false);
        }
      }
    },
    [businessId, isSending],
  );

  return { entries, isSending, failure, messagesLeft, send, restart };
}
