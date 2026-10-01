"use client";

import { useEffect, useId, useRef, useState, useSyncExternalStore, type FormEvent, type KeyboardEvent } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { describeError } from "@/api/errors";
import { useApiMutation } from "@/api/hooks";
import { unwrap } from "@/api/result";
import type { Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconRefresh, IconSend, IconWrench } from "@/components/content/icons";
import { IconAlert, IconChat, IconInfo, IconSparkles } from "@/components/icons";
import { Alert, Badge, Button, Card, EmptyState, ErrorState, Field, LoadingBlock, Select, Spinner, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  defaultTestVersionId,
  newSessionKey,
  parseStoredTestChat,
  prettyJson,
  sortVersions,
  type AssistantVersionSummary,
  type MessageView,
  type StoredTestChat,
} from "@/lib/assistant";
import { cn } from "@/lib/cn";

import { useAssistant } from "./_components/AssistantContext";
import { VERSION_STATUS_LABELS } from "./_components/VersionStatusBadge";
import { TOOL_LABELS } from "./versions/[versionId]/VersionDetailScreen";

type AssistantReply = Schema<"AssistantReply">;
type ToolCallView = Schema<"ToolCallView">;

const MAX_MESSAGE_LENGTH = 2000;

type ChatEntry =
  | { kind: "customer"; key: string; text: string; status: "sending" | "sent" | "failed"; error?: ApiError }
  | {
      kind: "assistant";
      key: string;
      text: string;
      reply?: AssistantReply;
      toolCalls?: ToolCallView[];
      /** The version that answered (from the reply, or the restored conversation). */
      versionId: string | null;
      versionNumber?: number | null;
    }
  | { kind: "silent"; key: string }
  | { kind: "note"; key: string; author: "staff" | "system"; text: string };

const SUGGESTIONS: readonly MessageKey[] = [
  "assistant.chat.suggestions.hours",
  "assistant.chat.suggestions.price",
  "assistant.chat.suggestions.booking",
  "assistant.chat.suggestions.human",
];

const subscribeNever = () => () => {};

function storageKey(businessId: string): string {
  return `aw:test-chat:${businessId}`;
}

function readStored(businessId: string): StoredTestChat | null {
  try {
    return parseStoredTestChat(window.sessionStorage.getItem(storageKey(businessId)));
  } catch {
    return null;
  }
}

function writeStored(businessId: string, value: StoredTestChat): void {
  try {
    window.sessionStorage.setItem(storageKey(businessId), JSON.stringify(value));
  } catch {
    // Storage can be unavailable (private mode); the chat still works.
  }
}

function entriesFromMessages(messages: readonly MessageView[], versionId: string | null): ChatEntry[] {
  return [...messages]
    .sort((left, right) => left.created_at - right.created_at)
    .map((message): ChatEntry => {
      if (message.author === "customer") {
        return { kind: "customer", key: message.id, text: message.text, status: "sent" };
      }
      if (message.author === "assistant") {
        return { kind: "assistant", key: message.id, text: message.text, toolCalls: message.tool_calls ?? [], versionId };
      }
      return { kind: "note", key: message.id, author: message.author, text: message.text };
    });
}

/**
 * Assistant -> Test chat: the owner writes as a customer to any version.
 * Test conversations are sandboxed (no billing, no staff notifications);
 * each reply shows the tools the assistant called.
 */
export function TestChatScreen({ initialVersionId }: { initialVersionId: string | null }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const { versions, openBuild } = useAssistant();
  const list = sortVersions(versions.data ?? []);
  // The chat restores its conversation from this tab's storage, so it is rendered in the browser only.
  const isBrowser = useSyncExternalStore(subscribeNever, () => true, () => false);

  if (!isBrowser || (versions.isLoading && !versions.data)) {
    return (
      <Card>
        <LoadingBlock label={t("common.loading")} />
      </Card>
    );
  }
  if (versions.error && !versions.data) {
    return (
      <Card>
        <ErrorState error={versions.error} onRetry={versions.reload} />
      </Card>
    );
  }
  if (list.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={<IconChat className="size-6" />}
          title={t("assistant.chat.noVersionsTitle")}
          description={isOwner ? t("assistant.chat.noVersionsDescription") : t("assistant.versions.emptyStaff")}
          action={
            isOwner ? (
              <Button leadingIcon={<IconSparkles className="size-4" aria-hidden />} onClick={openBuild}>
                {t("assistant.build.open")}
              </Button>
            ) : undefined
          }
        />
      </Card>
    );
  }

  return <TestChat key={business.id} versions={list} initialVersionId={initialVersionId} />;
}

function TestChat({
  versions,
  initialVersionId,
}: {
  versions: AssistantVersionSummary[];
  initialVersionId: string | null;
}) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const formId = useId();
  const scroller = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const sequence = useRef(0);

  const known = (id: string | null | undefined): id is string => Boolean(id && versions.some((version) => version.id === id));

  const [session, setSession] = useState<StoredTestChat>(() => {
    const stored = readStored(business.id);
    if (known(initialVersionId)) {
      return stored && stored.versionId === initialVersionId
        ? stored
        : { sessionKey: newSessionKey(), versionId: initialVersionId, conversationId: null };
    }
    if (stored && known(stored.versionId)) {
      return stored;
    }
    return { sessionKey: newSessionKey(), versionId: defaultTestVersionId(versions), conversationId: null };
  });
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isRestoring, setRestoring] = useState(session.conversationId !== null);
  const [isHandedOff, setHandedOff] = useState(false);
  const [text, setText] = useState("");

  const send = useApiMutation(
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

  const startNew = (versionId: string | null = session.versionId) => {
    setSession({ sessionKey: newSessionKey(), versionId, conversationId: null });
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

  const versionLabel = (id: string | null, number?: number | null) => {
    const version = versions.find((item) => item.id === id);
    if (version) {
      return t("assistant.chat.versionOption", { number: version.version_number, status: t(VERSION_STATUS_LABELS[version.status]) });
    }
    return number ? t("assistant.versions.number", { number }) : t("assistant.chat.unknownVersion");
  };
  const selected = versions.find((version) => version.id === session.versionId);

  return (
    <Card padded={false}>
      <div className="flex flex-col gap-3 border-b border-line px-4 py-4 sm:flex-row sm:items-end sm:justify-between sm:px-6">
        <Field label={t("assistant.chat.version")} className="sm:w-80">
          {(control) => (
            <Select
              {...control}
              value={session.versionId ?? ""}
              disabled={send.isPending}
              onChange={(event) => startNew(event.target.value)}
            >
              {versions.map((version) => (
                <option key={version.id} value={version.id}>
                  {versionLabel(version.id)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Button variant="secondary" leadingIcon={<IconRefresh className="size-4" aria-hidden />} onClick={() => startNew()} disabled={send.isPending}>
          {t("assistant.chat.newConversation")}
        </Button>
      </div>
      <p className="flex items-start gap-2 border-b border-line bg-surface-muted/50 px-4 py-2.5 text-sm text-ink-muted sm:px-6">
        <IconInfo className="mt-0.5 size-4 shrink-0" aria-hidden />
        {selected?.status === "archived" || selected?.status === "tests_failed"
          ? t("assistant.chat.sandboxNoteRisky", { version: versionLabel(session.versionId) })
          : t("assistant.chat.sandboxNote")}
      </p>

      <div
        ref={scroller}
        role="log"
        aria-live="polite"
        aria-label={t("assistant.chat.logLabel")}
        className="h-[min(60vh,36rem)] min-h-72 space-y-4 overflow-y-auto px-4 py-5 sm:px-6"
      >
        {isRestoring ? (
          <LoadingBlock label={t("common.loading")} />
        ) : entries.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="flex size-12 items-center justify-center rounded-full bg-accent-soft text-accent" aria-hidden>
              <IconChat className="size-6" />
            </div>
            <div className="space-y-1">
              <p className="font-medium text-ink">{t("assistant.chat.emptyTitle")}</p>
              <p className="max-w-md text-sm text-ink-muted">{t("assistant.chat.emptyDescription")}</p>
            </div>
            <div className="flex max-w-xl flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => void deliver(t(key))}
                  className="rounded-full border border-line-strong bg-surface px-3 py-1.5 text-sm text-ink hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-focus"
                >
                  {t(key)}
                </button>
              ))}
            </div>
          </div>
        ) : (
          entries.map((entry) => (
            <ChatLine
              key={entry.key}
              entry={entry}
              versionLabel={versionLabel}
              onRetry={(message, key) => void deliver(message, key)}
              isSending={send.isPending}
            />
          ))
        )}
        {send.isPending ? (
          <div className="flex items-center gap-2 text-sm text-ink-muted" role="status">
            <Spinner size="sm" /> {t("assistant.chat.typing")}
          </div>
        ) : null}
      </div>

      {isHandedOff ? (
        <Alert
          tone="info"
          className="mx-4 mb-3 sm:mx-6"
          title={t("assistant.chat.handedOffTitle")}
          action={
            <Button size="sm" variant="secondary" onClick={() => startNew()}>
              {t("assistant.chat.newConversation")}
            </Button>
          }
        >
          {t("assistant.chat.handedOffDescription")}
        </Alert>
      ) : null}

      <form id={formId} onSubmit={submit} className="flex items-end gap-2 border-t border-line px-4 py-3 sm:px-6">
        <label htmlFor={`${formId}-text`} className="sr-only">
          {t("assistant.chat.inputLabel")}
        </label>
        <Textarea
          ref={input}
          id={`${formId}-text`}
          rows={2}
          dir="auto"
          value={text}
          maxLength={MAX_MESSAGE_LENGTH}
          placeholder={t("assistant.chat.placeholder")}
          aria-describedby={`${formId}-hint`}
          className="min-h-11 resize-none"
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
        />
        <Button
          type="submit"
          aria-label={t("assistant.chat.send")}
          disabled={text.trim() === "" || send.isPending}
          className="h-11"
          leadingIcon={<IconSend className="size-4" aria-hidden />}
        >
          <span className="sr-only sm:not-sr-only">{t("assistant.chat.send")}</span>
        </Button>
      </form>
      <p id={`${formId}-hint`} className="px-4 pb-3 text-xs text-ink-subtle sm:px-6">
        {tp("assistant.chat.inputHint", MAX_MESSAGE_LENGTH)}
      </p>
    </Card>
  );
}

function ChatLine({
  entry,
  versionLabel,
  onRetry,
  isSending,
}: {
  entry: ChatEntry;
  versionLabel: (id: string | null, number?: number | null) => string;
  onRetry: (message: string, key: string) => void;
  isSending: boolean;
}) {
  const { t, tp } = useI18n();

  if (entry.kind === "customer") {
    const failure = entry.error ? describeError(entry.error, t, { external_service_error: "assistant.chat.errors.service" }) : null;
    return (
      <div className="flex flex-col items-end gap-1">
        <p className="mb-0.5 text-xs font-medium text-ink-subtle">{t("assistant.authors.customer")}</p>
        <div
          className={cn(
            "max-w-[85%] rounded-2xl rounded-br-md bg-accent-solid px-4 py-2.5 text-sm break-words whitespace-pre-wrap text-on-accent",
            entry.status === "sending" && "opacity-70",
            entry.status === "failed" && "bg-danger-soft text-ink ring-1 ring-danger/30",
          )}
          dir="auto"
        >
          {entry.text}
        </div>
        {entry.status === "failed" && failure ? (
          <div role="alert" className="flex max-w-[85%] flex-wrap items-center justify-end gap-2 text-sm text-danger">
            <IconAlert className="size-4 shrink-0" aria-hidden />
            <span>
              {t("assistant.chat.failed")} {failure.title}
              {failure.detail ? ` ${failure.detail}` : ""}
              {failure.requestId ? ` ${t("common.requestId", { id: failure.requestId })}` : ""}
            </span>
            <Button size="sm" variant="secondary" disabled={isSending} onClick={() => onRetry(entry.text, entry.key)}>
              {t("common.retry")}
            </Button>
          </div>
        ) : null}
      </div>
    );
  }

  if (entry.kind === "silent") {
    return <p className="mx-auto max-w-md text-center text-sm text-ink-muted">{t("assistant.chat.silent")}</p>;
  }

  if (entry.kind === "note") {
    return (
      <div className="mx-auto max-w-[85%] rounded-xl bg-warning-soft px-4 py-2 text-sm text-ink-muted">
        <span className="mb-0.5 block text-xs font-medium">{t(`assistant.authors.${entry.author}`)}</span>
        <span dir="auto" className="break-words whitespace-pre-wrap">
          {entry.text}
        </span>
      </div>
    );
  }

  const reply = entry.reply;
  const toolCalls = entry.toolCalls ?? [];
  const badges: { tone: "warning" | "info" | "success"; label: string }[] = [];
  if (reply?.guard_verdict === "rewritten") {
    badges.push({ tone: "warning", label: t("assistant.chat.guardRewritten") });
  }
  if (reply?.guard_verdict === "handed_off") {
    badges.push({ tone: "warning", label: t("assistant.chat.guardHandedOff") });
  }
  if ((reply?.created_booking_ids ?? []).length > 0) {
    badges.push({ tone: "success", label: tp("assistant.chat.bookingsCreated", (reply?.created_booking_ids ?? []).length) });
  }
  if ((reply?.created_lead_ids ?? []).length > 0) {
    badges.push({ tone: "success", label: tp("assistant.chat.leadsCreated", (reply?.created_lead_ids ?? []).length) });
  }
  if ((reply?.created_handoff_ids ?? []).length > 0 || reply?.is_handed_off) {
    badges.push({ tone: "info", label: t("assistant.chat.handedOff") });
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <p className="mb-0.5 text-xs font-medium text-ink-subtle">
        {t("assistant.authors.assistant")}
        {entry.versionId ? ` · ${versionLabel(entry.versionId, entry.versionNumber)}` : ""}
      </p>
      <div className="max-w-[85%] rounded-2xl rounded-bl-md bg-surface-muted px-4 py-2.5 text-sm break-words whitespace-pre-wrap text-ink" dir="auto">
        {entry.text}
      </div>
      {badges.length > 0 ? (
        <div className="flex max-w-[85%] flex-wrap gap-1.5">
          {badges.map((badge) => (
            <Badge key={badge.label} tone={badge.tone}>
              {badge.label}
            </Badge>
          ))}
        </div>
      ) : null}
      {toolCalls.length > 0 ? (
        <details className="w-full max-w-[85%] rounded-xl border border-line">
          <summary className="flex cursor-pointer items-center gap-2 rounded-xl px-3 py-2 text-sm text-ink-muted hover:bg-surface-muted/60 focus-visible:outline-2 focus-visible:outline-focus">
            <IconWrench className="size-4" aria-hidden />
            {tp("assistant.chat.toolCalls", toolCalls.length)}
          </summary>
          <ol className="space-y-3 border-t border-line px-3 py-3">
            {toolCalls.map((call, index) => (
              <li key={index} className="space-y-1.5">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
                  {t(TOOL_LABELS[call.tool_name].name)}
                  <code className="text-xs font-normal text-ink-subtle">{call.tool_name}</code>
                  {call.is_error ? <Badge tone="danger">{t("assistant.chat.toolError")}</Badge> : null}
                </p>
                <p className="text-xs font-medium text-ink-subtle">{t("assistant.chat.toolInput")}</p>
                <pre className="max-h-48 overflow-auto rounded-lg bg-surface-muted p-2 text-xs break-words whitespace-pre-wrap text-ink">
                  {prettyJson(call.input_json)}
                </pre>
                <p className="text-xs font-medium text-ink-subtle">{t("assistant.chat.toolResult")}</p>
                <pre className="max-h-48 overflow-auto rounded-lg bg-surface-muted p-2 text-xs break-words whitespace-pre-wrap text-ink">
                  {prettyJson(call.result_json)}
                </pre>
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </div>
  );
}
