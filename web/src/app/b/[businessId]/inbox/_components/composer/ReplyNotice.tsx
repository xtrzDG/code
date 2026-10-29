"use client";

/**
 * What the composer says above the text when writing is limited: why the
 * channel cannot carry a message now (a call, a test, a closed 24-hour
 * window, a disconnected channel), that the text will go out in the
 * owner's WhatsApp template, or that Meta refused that template. Owners
 * get a way to the Channels page where it can be fixed.
 */

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import type { ConversationSummaryView, StaffReplyView } from "@/components/insights/types";
import { Alert, ButtonLink } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { REPLY_BLOCKS } from "../../_lib/conversationModel";
import type { StaffReply } from "../../_lib/useStaffReply";

export function ReplyNotice({
  conversation,
  reply,
  staffReply,
}: {
  conversation: ConversationSummaryView;
  reply: StaffReplyView;
  staffReply: StaffReply;
}) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const { template, channel } = staffReply;

  const channelsLink = isOwner ? (
    <ButtonLink href={businessPath(business.id, "assistant/channels")} variant="secondary" size="sm">
      {t("conversations.reply.openChannels")}
    </ButtonLink>
  ) : undefined;
  const windowClosedAt =
    reply.block === "window_closed" && reply.window_closes_at ? (
      <p className="mt-1 text-ink-muted">
        {t("conversations.reply.windowClosedAt", { date: format.dateTime(reply.window_closes_at) })}
      </p>
    ) : null;

  if (!staffReply.canWrite) {
    const needsTemplate = reply.block === "window_closed" && conversation.channel === "whatsapp";
    return (
      <Alert tone="info" className="mb-2" action={needsTemplate ? channelsLink : undefined}>
        <p>{reply.block ? t(REPLY_BLOCKS[reply.block], { channel }) : t("conversations.reply.unavailable")}</p>
        {windowClosedAt}
        {needsTemplate ? (
          <p className="mt-1">{t(isOwner ? "conversations.reply.noTemplateOwner" : "conversations.reply.noTemplateStaff")}</p>
        ) : null}
      </Alert>
    );
  }

  if (template && staffReply.isTemplateRejected) {
    return (
      <Alert tone="danger" className="mb-2" action={channelsLink}>
        {t(isOwner ? "conversations.reply.template.rejectedOwner" : "conversations.reply.template.rejectedStaff", {
          name: template.name,
        })}
      </Alert>
    );
  }

  if (template) {
    return (
      <Alert tone="info" className="mb-2">
        <p>{t("conversations.reply.template.intro")}</p>
        {windowClosedAt}
      </Alert>
    );
  }
  return null;
}
