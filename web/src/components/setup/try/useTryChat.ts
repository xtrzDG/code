"use client";

/**
 * The test chat of "Try it": the owner writes as a customer would and the
 * assistant answers from what the tunnel saved so far (the API prepares a
 * preview of it). The lines stay on this screen; "Start over" opens a new
 * conversation.
 */

import { useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { newTrySessionKey } from "@/lib/tunnel/tryQuestions";

export interface TryLine {
  key: string;
  from: "you" | "assistant";
  text: string;
  status: "sending" | "sent" | "failed";
}

export function useTryChat(businessId: string) {
  const [sessionKey, setSessionKey] = useState(() => newTrySessionKey());
  const [lines, setLines] = useState<TryLine[]>([]);
  const [isHandedOff, setHandedOff] = useState(false);
  const [hasReply, setHasReply] = useState(false);
  const sequence = useRef(0);
  const scroller = useRef<HTMLDivElement>(null);

  const send = useMutation(
    (text: string, session: string) =>
      api.POST("/v1/businesses/{business_id}/test-chat", {
        params: { path: { business_id: businessId } },
        body: { text, session_key: session },
      }),
    { errorToast: false, stale: [queryKeys.setup.all(businessId), queryKeys.assistant.all(businessId)] },
  );

  // Keep the newest line in view.
  useEffect(() => {
    const node = scroller.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [lines, send.isPending]);

  const nextKey = () => {
    sequence.current += 1;
    return `line-${sequence.current}`;
  };

  const mark = (key: string, status: TryLine["status"]) =>
    setLines((current) => current.map((line) => (line.key === key ? { ...line, status } : line)));

  /** Send a message (or send a failed one again, by its key). */
  const deliver = async (text: string, retryKey?: string) => {
    const key = retryKey ?? nextKey();
    if (retryKey) {
      mark(retryKey, "sending");
    } else {
      setLines((current) => [...current, { key, from: "you", text, status: "sending" }]);
    }
    const result = await send.run(text, sessionKey);
    if (!result.ok) {
      mark(key, "failed");
      return;
    }
    mark(key, "sent");
    const reply = result.data.text;
    if (reply) {
      setLines((current) => [...current, { key: nextKey(), from: "assistant", text: reply, status: "sent" }]);
    }
    setHandedOff(result.data.is_handed_off);
    setHasReply(true);
  };

  const restart = () => {
    setSessionKey(newTrySessionKey());
    setLines([]);
    setHandedOff(false);
  };

  return { scroller, lines, isSending: send.isPending, isHandedOff, hasReply, deliver, restart };
}
