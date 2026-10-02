"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState, type ReactNode } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconArrowLeft } from "@/components/icons";
import { AfterHoursBadge, ChannelBadge, ConversationStatusBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName, PhoneLink } from "@/components/insights/common";
import { CustomerMessageModal } from "@/components/insights/CustomerMessageModal";
import { formatMicroUsd } from "@/components/insights/numbers";
import type {
  ConversationDetailView,
  ConversationRating,
  ConversationSummaryView,
  MessageView,
} from "@/components/insights/types";
import { Alert, Card, ErrorState, LoadingBlock, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { BookFromConversation } from "./BookFromConversation";
import { CallsCard } from "./CallsCard";
import { canReplyFromCard, initialsOf, usageTotals } from "./conversationModel";
import { LinkedItems } from "./LinkedItems";
import { RatingControl } from "./RatingControl";
import { ReplyBox } from "./ReplyBox";
import { Transcript } from "./Transcript";

/**
 * The conversation card: who, where, how it was rated, what came out of it
 * (bookings, leads, handoffs), the calls, the transcript with the
 * assistant's actions, and a reply box for staff.
 */
export function ConversationDetail({ conversationId }: { conversationId: string }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const searchParams = useSearchParams();
  const businessId = business.id;
  const listQuery = searchParams.toString();
  const backHref = `${businessPath(businessId, "conversations")}${listQuery ? `?${listQuery}` : ""}`;
  const [draft, setDraft] = useState("");
  const [isBooking, setIsBooking] = useState(false);
  const [confirmation, setConfirmation] = useState<string | null>(null);

  const detail = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/conversations/{conversation_id}", {
        params: { path: { business_id: businessId, conversation_id: conversationId } },
      }),
    [businessId, conversationId],
  );
  // No auto-refresh here: every card view is written to the audit log.

  const rate = useApiMutation((rating: ConversationRating | null) =>
    api.PUT("/v1/businesses/{business_id}/conversations/{conversation_id}/rating", {
      params: { path: { business_id: businessId, conversation_id: conversationId } },
      body: { rating },
    }),
  );

  const backLink = (
    <Link
      href={backHref}
      className="mb-4 inline-flex items-center gap-1.5 rounded-lg text-sm font-medium text-accent hover:underline lg:hidden"
    >
      <IconArrowLeft className="size-4" aria-hidden />
      {t("conversations.back")}
    </Link>
  );

  if (!detail.data || detail.data.conversation.id !== conversationId) {
    return (
      <>
        {backLink}
        <Card>
          {detail.error ? (
            <ErrorState error={detail.error} onRetry={detail.reload} />
          ) : (
            <LoadingBlock label={t("conversations.loadingOne")} />
          )}
        </Card>
      </>
    );
  }

  const data = detail.data;
  const { conversation } = data;
  const messages = data.messages ?? [];
  const reply = data.reply ?? null;

  const updateDetail = (update: (current: ConversationDetailView) => ConversationDetailView) =>
    detail.setData((current) => (current ? update(current) : data));

  const changeRating = async (rating: ConversationRating | null) => {
    const result = await rate.run(rating);
    if (result.ok) {
      updateDetail((current) => ({ ...current, conversation: result.data }));
      toast.success(t(rating === null ? "conversations.rating.cleared" : "conversations.rating.saved"));
    }
  };

  const addMessage = (message: MessageView) =>
    updateDetail((current) => ({
      ...current,
      messages: [...(current.messages ?? []), message],
      conversation: {
        ...current.conversation,
        message_count: current.conversation.message_count + 1,
        last_message_at: Math.max(current.conversation.last_message_at, message.created_at),
      },
    }));

  return (
    <article className="space-y-4" aria-labelledby="conversation-title">
      {backLink}
      <ConversationHeader
        conversation={conversation}
        messageCount={messages.length}
        totals={usageTotals(messages)}
        rating={
          <RatingControl
            value={conversation.rating ?? null}
            isPending={rate.isPending}
            onChange={(rating) => void changeRating(rating)}
          />
        }
      />

      {conversation.status === "handoff" ? (
        <Alert tone="warning">
          <p>{t("conversations.handoffNotice")}</p>
          <Link
            href={businessPath(businessId, "handoffs")}
            className="mt-1 inline-block font-medium text-accent hover:underline"
          >
            {t("conversations.toHandoffs")}
          </Link>
        </Alert>
      ) : null}

      <LinkedItems detail={data} onBook={conversation.is_sandbox ? null : () => setIsBooking(true)} />

      {(data.calls ?? []).length > 0 ? <CallsCard calls={data.calls ?? []} /> : null}

      <Card title={t("conversations.transcript")}>
        <Transcript messages={messages} />
      </Card>

      {reply ? (
        <ReplyBox
          conversation={conversation}
          reply={reply}
          draft={draft}
          onDraft={setDraft}
          onSent={(message) => {
            addMessage(message);
            setDraft("");
          }}
          onRefused={detail.reload}
        />
      ) : null}

      <BookFromConversation
        open={isBooking}
        conversation={conversation}
        onClose={() => setIsBooking(false)}
        onCreated={(result) => {
          setIsBooking(false);
          detail.reload();
          toast.success(t("bookings.created"));
          // The reply box takes it freely or, past WhatsApp's 24 hours, in
          // the owner's template; otherwise staff copy it by hand.
          if (canReplyFromCard(reply)) {
            setDraft(result.confirmation_text);
            toast.info(t("conversations.reply.confirmationPrefilled"));
          } else {
            setConfirmation(result.confirmation_text);
          }
        }}
      />

      <CustomerMessageModal
        open={confirmation !== null}
        title={t("bookings.created")}
        text={confirmation ?? ""}
        onClose={() => setConfirmation(null)}
      />
    </article>
  );
}

function ConversationHeader({
  conversation,
  messageCount,
  totals,
  rating,
}: {
  conversation: ConversationSummaryView;
  messageCount: number;
  totals: ReturnType<typeof usageTotals>;
  rating: ReactNode;
}) {
  const { t, tp, locale } = useI18n();
  const format = useBusinessFormat();
  const tokens = totals.inputTokens + totals.outputTokens;

  return (
    <Card>
      <div className="flex items-start gap-4">
        <span
          className="flex size-12 shrink-0 items-center justify-center rounded-full bg-accent-soft text-base font-semibold text-accent-ink"
          aria-hidden
        >
          {initialsOf(conversation.contact_name)}
        </span>
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="conversation-title" className="text-lg font-semibold text-ink">
              <CustomerName name={conversation.contact_name} />
            </h2>
            <ConversationStatusBadge status={conversation.status} />
            {conversation.is_after_hours ? <AfterHoursBadge /> : null}
            {conversation.is_sandbox ? <TestBadge /> : null}
          </div>
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
            {conversation.contact_phone_number ? (
              <PhoneLink phone={conversation.contact_phone_number} />
            ) : (
              <span>{t("conversations.noPhone")}</span>
            )}
            <ChannelBadge channel={conversation.channel} />
            {conversation.language ? <span>{languageName(conversation.language, locale)}</span> : null}
          </p>
        </div>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-line pt-4 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-ink-muted">{t("conversations.started")}</dt>
          <dd className="text-ink">{format.dateTime(conversation.created_at)}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">{t("conversations.lastMessage")}</dt>
          <dd className="text-ink">{format.dateTime(conversation.last_message_at)}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">{t("conversations.usage.tokens")}</dt>
          <dd className="text-ink tabular-nums">
            {tokens > 0
              ? t("conversations.usage.tokensValue", {
                  input: format.number(totals.inputTokens),
                  output: format.number(totals.outputTokens),
                })
              : "–"}
          </dd>
        </div>
        <div>
          <dt className="text-ink-muted">{t("conversations.usage.cost")}</dt>
          <dd className="text-ink tabular-nums">{formatMicroUsd(totals.costMicroUsd, locale)}</dd>
        </div>
      </dl>
      <div className="mt-4 border-t border-line pt-4">{rating}</div>
      <p className="sr-only">{tp("conversations.messages", messageCount)}</p>
    </Card>
  );
}
