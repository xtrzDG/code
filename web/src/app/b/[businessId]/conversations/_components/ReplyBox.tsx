"use client";

import { useId, useState, type FormEvent, type KeyboardEvent } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { CHANNEL_LABELS } from "@/components/insights/labels";
import type { ConversationSummaryView, MessageView, StaffReplyView } from "@/components/insights/types";
import { Alert, Button, Card, Textarea, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { isSendableReply, isWindowClosingSoon, MAX_REPLY_LENGTH, REPLY_BLOCKS } from "./conversationModel";

/**
 * Staff write to the customer from the card (POST …/messages). The message
 * goes out through the conversation's channel (Telegram, WhatsApp,
 * Instagram, Messenger) or waits in the website chat; the assistant does
 * not answer it. When the channel cannot carry a message now (a call, a
 * test, a closed 24-hour window), the box says why instead.
 */
export function ReplyBox({
  conversation,
  reply,
  draft,
  onDraft,
  onSent,
  onRefused,
}: {
  conversation: ConversationSummaryView;
  reply: StaffReplyView;
  draft: string;
  onDraft: (text: string) => void;
  onSent: (message: MessageView) => void;
  /** The API refused (the window closed meanwhile): load the card again. */
  onRefused: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const id = useId();
  const [now] = useState(() => Date.now());
  const channel = t(CHANNEL_LABELS[conversation.channel]);

  const send = useApiMutation(
    (text: string) =>
      api.POST("/v1/businesses/{business_id}/conversations/{conversation_id}/messages", {
        params: { path: { business_id: business.id, conversation_id: conversation.id } },
        body: { text },
      }),
    { errorMessages: { conflict: "conversations.reply.refused" } },
  );

  if (!reply.is_available) {
    return (
      <Card title={t("conversations.reply.title")}>
        <Alert tone="info">
          <p>{reply.block ? t(REPLY_BLOCKS[reply.block], { channel }) : t("conversations.reply.unavailable")}</p>
          {reply.block === "window_closed" && reply.window_closes_at ? (
            <p className="mt-1 text-ink-muted">
              {t("conversations.reply.windowClosedAt", { date: format.dateTime(reply.window_closes_at) })}
            </p>
          ) : null}
        </Alert>
      </Card>
    );
  }

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!isSendableReply(draft) || send.isPending) {
      return;
    }
    const result = await send.run(draft.trim());
    if (result.ok) {
      onSent(result.data.message);
      toast.success(
        t(result.data.delivery === "sent" ? "conversations.reply.sent" : "conversations.reply.stored", { channel }),
      );
    } else if (result.error.code === "conflict") {
      onRefused();
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submit();
    }
  };

  const closesSoon = isWindowClosingSoon(reply.window_closes_at, now);
  const tooLong = draft.length > MAX_REPLY_LENGTH;
  return (
    <Card title={t("conversations.reply.title")}>
      <form onSubmit={(event) => void submit(event)} className="space-y-3">
        <label htmlFor={`${id}-text`} className="sr-only">
          {t("conversations.reply.label")}
        </label>
        <Textarea
          id={`${id}-text`}
          dir="auto"
          rows={3}
          value={draft}
          onChange={(event) => onDraft(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={t("conversations.reply.placeholder")}
          aria-describedby={`${id}-hint`}
          aria-invalid={tooLong || undefined}
          disabled={send.isPending}
        />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div id={`${id}-hint`} className="space-y-1 text-xs text-ink-muted">
            <p>
              {reply.delivery === "stored_for_widget"
                ? t("conversations.reply.widgetHint")
                : t("conversations.reply.channelHint", { channel })}
            </p>
            {reply.window_closes_at ? (
              <p className={closesSoon ? "font-medium text-warning" : undefined}>
                {t("conversations.reply.windowOpenUntil", { channel, date: format.dateTime(reply.window_closes_at) })}
              </p>
            ) : null}
            <p className={tooLong ? "text-danger" : undefined}>
              {t("conversations.reply.length", { count: draft.length, max: MAX_REPLY_LENGTH })}
            </p>
          </div>
          <Button
            type="submit"
            className="shrink-0 self-end sm:self-start"
            disabled={!isSendableReply(draft)}
            isLoading={send.isPending}
            loadingText={t("conversations.reply.sending")}
          >
            {t("conversations.reply.send")}
          </Button>
        </div>
      </form>
    </Card>
  );
}
