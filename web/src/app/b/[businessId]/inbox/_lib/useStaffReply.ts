"use client";

/**
 * Sending a staff message from the conversation (POST …/messages): through
 * the conversation's channel, kept for the website chat, or, after
 * WhatsApp's 24 hours, in the owner's approved template. A template Meta
 * refused stays refused until the owner fixes it, so the composer says so
 * instead of offering a retry; a closed window found on sending reloads
 * the card.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { CHANNEL_LABELS } from "@/components/insights/labels";
import type { ConversationSummaryView, MessageView, StaffReplyView } from "@/components/insights/types";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { placeholdersIn } from "@/lib/quickReplies";

import {
  isSendableReply,
  isSendableTemplateReply,
  MAX_REPLY_LENGTH,
  offeredTemplate,
  templateReplyLength,
} from "./conversationModel";

/** The refusal reason of a WhatsApp template Meta did not accept. */
export const TEMPLATE_REJECTED = "template_rejected";

export function useStaffReply({
  conversation,
  reply,
  onSent,
  onRefused,
}: {
  conversation: ConversationSummaryView;
  reply: StaffReplyView;
  onSent: (message: MessageView) => void;
  /** The API refused (the window closed meanwhile): load the card again. */
  onRefused: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business, isOwner } = useBusiness();
  const channel = t(CHANNEL_LABELS[conversation.channel]);
  // Offered only once the WhatsApp window has closed and the owner set one.
  const template = offeredTemplate(reply);
  const [isTemplateRejected, setTemplateRejected] = useState(false);

  const send = useMutation(
    (text: string, asTemplate: boolean) =>
      api.POST("/v1/businesses/{business_id}/conversations/{conversation_id}/messages", {
        params: { path: { business_id: business.id, conversation_id: conversation.id } },
        body: asTemplate ? { text, as_template: true } : { text },
      }),
    {
      errorMessages: { conflict: "conversations.reply.refused" },
      reasonMessages: {
        [TEMPLATE_REJECTED]: () => ({
          key: isOwner ? "conversations.reply.template.rejectedOwner" : "conversations.reply.template.rejectedStaff",
          values: { name: template?.name ?? "" },
        }),
      },
    },
  );

  const maxLength = template ? template.max_text_length : MAX_REPLY_LENGTH;
  const lengthOf = (draft: string) => (template ? templateReplyLength(draft) : draft.length);
  const isTooLong = (draft: string) => lengthOf(draft) > maxLength || draft.length > MAX_REPLY_LENGTH;
  const isSendable = (draft: string) =>
    placeholdersIn(draft).length === 0 &&
    (template
      ? draft.length <= MAX_REPLY_LENGTH && isSendableTemplateReply(draft, template.max_text_length)
      : isSendableReply(draft));

  /** Sends the draft; true when it went out (the composer then clears it). */
  const submit = async (draft: string): Promise<boolean> => {
    if (!isSendable(draft) || send.isPending) {
      return false;
    }
    const result = await send.run(draft.trim(), template !== null);
    if (result.ok) {
      setTemplateRejected(false);
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
      return true;
    }
    if (result.error.reasons.some((reason) => reason.code === TEMPLATE_REJECTED)) {
      setTemplateRejected(true);
    } else if (result.error.code === "conflict") {
      onRefused();
    }
    return false;
  };

  return {
    channel,
    template,
    isTemplateRejected,
    canWrite: reply.is_available || template !== null,
    maxLength,
    lengthOf,
    isTooLong,
    isSendable,
    submit,
    isSending: send.isPending,
  };
}

export type StaffReply = ReturnType<typeof useStaffReply>;
