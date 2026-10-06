"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { unwrap } from "@/api/result";
import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";
import { answeredTarget, chatChoices, initialTarget, storedTarget, type ChatChoice, type ChatTarget } from "@/lib/assistant/chatTargets";
import { newSessionKey, type StoredTestChat } from "@/lib/assistant/testChat";
import type { AssistantVersionSummary } from "@/lib/assistant/versions";

import { entriesFromMessages, type ChatEntry } from "./chatEntries";
import { readStored, writeStored } from "./testChatStorage";

/**
 * One test conversation: who it talks to ("What customers get now", "With
 * your changes", or an update opened from History), its lines, sending
 * and retrying messages. The conversation is kept in this browser tab, so
 * a reload continues it.
 */
export function useTestChat(versions: AssistantVersionSummary[], initialVersionId: string | null) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const scroller = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const sequence = useRef(0);

  const known = (id: string | null | undefined): id is string => Boolean(id && versions.some((version) => version.id === id));
  // An update opened from History stays a choice while this page is open.
  const historyId = known(initialVersionId) ? initialVersionId : null;
  const choices = chatChoices(versions, historyId);
  const choiceOf = (target: ChatTarget): ChatChoice =>
    choices.find((choice) => choice.target === target) ?? { target: "changes", versionId: null, versionNumber: null };

  const [session, setSession] = useState<StoredTestChat>(() => {
    const stored = readStored(business.id);
    if (historyId) {
      const target = initialTarget(versions, historyId);
      return stored && stored.versionId === historyId
        ? { ...stored, target }
        : { sessionKey: newSessionKey(), versionId: historyId, conversationId: null, target };
    }
    if (stored && (stored.versionId === null || known(stored.versionId))) {
      const target = storedTarget(versions, stored);
      // A conversation with an earlier live version starts over with the one customers get now.
      const isStale = target === "live" && stored.versionId !== choices.find((choice) => choice.target === "live")?.versionId;
      if (!isStale && choices.some((choice) => choice.target === target)) {
        return { ...stored, target };
      }
    }
    return { sessionKey: newSessionKey(), versionId: null, conversationId: null, target: "changes" };
  });
  const target: ChatTarget = session.target ?? "changes";
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isRestoring, setRestoring] = useState(session.conversationId !== null);
  const [isHandedOff, setHandedOff] = useState(false);
  const [text, setText] = useState("");

  const send = useMutation(
    (message: string) =>
      api.POST("/v1/businesses/{business_id}/test-chat", {
        params: { path: { business_id: business.id } },
        body: { text: message, session_key: session.sessionKey, assistant_version_id: session.versionId },
      }),
    { errorToast: false },
  );

  const nextKey = () => {
    sequence.current += 1;
    return `local-${sequence.current}`;
  };

  // Remember the conversation in this browser tab.
  useEffect(() => {
    writeStored(business.id, session);
  }, [business.id, session]);

  // A reload continues the stored conversation.
  const restoreId = useRef(session.conversationId);
  useEffect(() => {
    const conversationId = restoreId.current;
    if (!conversationId) {
      return;
    }
    let active = true;
    unwrap(
      api.GET("/v1/businesses/{business_id}/conversations/{conversation_id}", {
        params: { path: { business_id: business.id, conversation_id: conversationId } },
      }),
    ).then(
      (detail) => {
        if (active) {
          setEntries(entriesFromMessages(detail.messages ?? [], detail.conversation.assistant_version_id));
          setHandedOff(detail.conversation.status === "handoff");
          setRestoring(false);
        }
      },
      () => {
        if (active) {
          // Gone or not readable: start over quietly.
          setSession((current) => ({ ...current, sessionKey: newSessionKey(), conversationId: null }));
          setRestoring(false);
        }
      },
    );
    return () => {
      active = false;
    };
  }, [business.id]);

  // Keep the newest message in view.
  useEffect(() => {
    const node = scroller.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [entries, send.isPending]);

  const startNew = (next: ChatTarget = target) => {
    setSession({ sessionKey: newSessionKey(), versionId: choiceOf(next).versionId, conversationId: null, target: next });
    setEntries([]);
    setHandedOff(false);
    input.current?.focus();
  };

  const deliver = async (message: string, retryKey?: string) => {
    const customerKey = retryKey ?? nextKey();
    setEntries((current) =>
      retryKey
        ? current.map((entry) => (entry.key === retryKey && entry.kind === "customer" ? { ...entry, status: "sending", error: undefined } : entry))
        : [...current, { kind: "customer", key: customerKey, text: message, status: "sending" }],
    );
    const result = await send.run(message);
    if (!result.ok) {
      setEntries((current) =>
        current.map((entry) =>
          entry.key === customerKey && entry.kind === "customer" ? { ...entry, status: "failed", error: result.error } : entry,
        ),
      );
      return;
    }
    // The reply names the version that answered and the tools it called,
    // so the conversation card (an audited read) is not needed here.
    const reply = result.data;
    const answeredBy = reply.assistant_version_id ?? session.versionId;
    setEntries((current) => [
      ...current.map((entry) => (entry.key === customerKey && entry.kind === "customer" ? { ...entry, status: "sent" as const } : entry)),
      reply.text === null || reply.text === undefined
        ? { kind: "silent", key: nextKey() }
        : {
            kind: "assistant",
            key: nextKey(),
            text: reply.text,
            reply,
            toolCalls: reply.tool_calls ?? [],
            choices: reply.choices?.options ?? [],
            versionId: answeredBy,
            versionNumber: reply.assistant_version_number ?? null,
          },
    ]);
    setHandedOff(reply.is_handed_off);
    setSession((current) => ({ ...current, versionId: current.versionId ?? answeredBy, conversationId: reply.conversation_id }));
  };

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const message = text.trim();
    if (message === "" || send.isPending) {
      return;
    }
    setText("");
    void deliver(message);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  };

  /** Which choice answered a line ("What customers get now", "With your changes", "From History: update 3"). */
  const answerLabel = (versionId: string | null, number?: number | null) => {
    const answered = answeredTarget(versions, versionId, historyId);
    return answered === "history" ? t("updates.chat.history", { number: number ?? choiceOf("history").versionNumber ?? "" }) : t(`updates.chat.${answered}`);
  };

  return {
    scroller,
    input,
    session,
    entries,
    isRestoring,
    isHandedOff,
    isSending: send.isPending,
    text,
    setText,
    startNew,
    deliver,
    submit,
    onKeyDown,
    target,
    choices,
    answerLabel,
  };
}
