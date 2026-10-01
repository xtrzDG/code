"use client";

import { useId, useState, type FormEvent, type KeyboardEvent } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { CHANNEL_LABELS } from "@/components/insights/labels";
import type { ConversationSummaryView, MessageView, StaffReplyView } from "@/components/insights/types";
import { Alert, Button, ButtonLink, Card, Textarea, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import {
  isSendableReply,
  isSendableTemplateReply,
  isWindowClosingSoon,
  MAX_REPLY_LENGTH,
  REPLY_BLOCKS,
  templateLanguageName,
  templateReplyLength,
} from "./conversationModel";

/**
 * Staff write to the customer from the card (POST …/messages). The message
 * goes out through the conversation's channel (Telegram, WhatsApp,
 * Instagram, Messenger) or waits in the website chat; the assistant does
 * not answer it. When the channel cannot carry a message now (a call, a
 * test, a closed 24-hour window), the box says why instead. After the
 * WhatsApp window has closed, the owner's approved template (set on the
 * Channels page) still carries the text: the box offers "Send as template",
 * or, without a template, points to the Channels page.
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
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const id = useId();
  const [now] = useState(() => Date.now());
  const channel = t(CHANNEL_LABELS[conversation.channel]);
  // Offered only once the WhatsApp window has closed and the owner set one.
  const template = !reply.is_available && reply.block === "window_closed" ? (reply.template ?? null) : null;

  const send = useApiMutation(
    (text: string, asTemplate: boolean) =>
      api.POST("/v1/businesses/{business_id}/conversations/{conversation_id}/messages", {
        params: { path: { business_id: business.id, conversation_id: conversation.id } },
        body: asTemplate ? { text, as_template: true } : { text },
      }),
    { errorMessages: { conflict: "conversations.reply.refused" } },
  );

  const windowClosedAt =
    reply.block === "window_closed" && reply.window_closes_at ? (
      <p className="mt-1 text-ink-muted">
        {t("conversations.reply.windowClosedAt", { date: format.dateTime(reply.window_closes_at) })}
      </p>
    ) : null;

  if (!reply.is_available && template === null) {
    const needsTemplate = reply.block === "window_closed" && conversation.channel === "whatsapp";
    return (
      <Card title={t("conversations.reply.title")}>
        <Alert
          tone="info"
          action={
            needsTemplate ? (
              <ButtonLink href={businessPath(business.id, "channels")} variant="secondary" size="sm">
                {t("conversations.reply.openChannels")}
              </ButtonLink>
            ) : undefined
          }
        >
          <p>{reply.block ? t(REPLY_BLOCKS[reply.block], { channel }) : t("conversations.reply.unavailable")}</p>
          {windowClosedAt}
          {needsTemplate ? (
            <p className="mt-1">
              {t(isOwner ? "conversations.reply.noTemplateOwner" : "conversations.reply.noTemplateStaff")}
            </p>
          ) : null}
        </Alert>
      </Card>
    );
  }

  const isSendable = template
    ? draft.length <= MAX_REPLY_LENGTH && isSendableTemplateReply(draft, template.max_text_length)
    : isSendableReply(draft);

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!isSendable || send.isPending) {
      return;
    }
    const result = await send.run(draft.trim(), template !== null);
    if (result.ok) {
      onSent(result.data.message);
      const delivery = result.data.delivery;
      toast.success(
        t(
          delivery === "sent_as_template"
            ? "conversations.reply.template.sent"
            : delivery === "sent"
              ? "conversations.reply.sent"
              : "conversations.reply.stored",
          { channel },
        ),
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
  const maxLength = template ? template.max_text_length : MAX_REPLY_LENGTH;
  const length = template ? templateReplyLength(draft) : draft.length;
  const tooLong = length > maxLength || draft.length > MAX_REPLY_LENGTH;
  return (
    <Card title={t("conversations.reply.title")}>
      {template ? (
        <Alert tone="info" className="mb-3">
          <p>{t("conversations.reply.template.intro")}</p>
          {windowClosedAt}
        </Alert>
      ) : null}
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
              {template
                ? t("conversations.reply.template.hint", {
                    name: template.name,
                    language: templateLanguageName(template.language_code, locale),
                  })
                : reply.delivery === "stored_for_widget"
                  ? t("conversations.reply.widgetHint")
                  : t("conversations.reply.channelHint", { channel })}
            </p>
            {reply.is_available && reply.window_closes_at ? (
              <p className={closesSoon ? "font-medium text-warning" : undefined}>
                {t("conversations.reply.windowOpenUntil", { channel, date: format.dateTime(reply.window_closes_at) })}
              </p>
            ) : null}
            <p className={tooLong ? "text-danger" : undefined}>
              {t("conversations.reply.length", { count: length, max: maxLength })}
            </p>
          </div>
          <Button
            type="submit"
            className="shrink-0 self-end sm:self-start"
            disabled={!isSendable}
            isLoading={send.isPending}
            loadingText={t("conversations.reply.sending")}
          >
            {template ? t("conversations.reply.template.send") : t("conversations.reply.send")}
          </Button>
        </div>
      </form>
    </Card>
  );
}
