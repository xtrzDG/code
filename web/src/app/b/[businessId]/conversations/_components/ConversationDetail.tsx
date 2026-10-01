"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconArrowLeft } from "@/components/icons";
import { AfterHoursBadge, ChannelBadge, ConversationStatusBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName, PhoneLink } from "@/components/insights/common";
import { formatMicroUsd } from "@/components/insights/numbers";
import type { ConversationSummaryView } from "@/components/insights/types";
import { Alert, Card, ErrorState, LoadingBlock } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { initialsOf, usageTotals } from "./conversationModel";
import { LinkedItems } from "./LinkedItems";
import { Transcript } from "./Transcript";

/** The conversation card: who, where, the transcript with actions and what came out of it. */
export function ConversationDetail({ conversationId }: { conversationId: string }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const searchParams = useSearchParams();
  const businessId = business.id;
  const listQuery = searchParams.toString();
  const backHref = `${businessPath(businessId, "conversations")}${listQuery ? `?${listQuery}` : ""}`;

  const detail = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/conversations/{conversation_id}", {
        params: { path: { business_id: businessId, conversation_id: conversationId } },
      }),
    [businessId, conversationId],
  );
  // No auto-refresh here: every card view is written to the audit log.

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

  const { conversation } = detail.data;
  const messages = detail.data.messages ?? [];
  return (
    <article className="space-y-4" aria-labelledby="conversation-title">
      {backLink}
      <ConversationHeader conversation={conversation} messageCount={messages.length} totals={usageTotals(messages)} />

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

      <LinkedItems conversation={conversation} />

      <Card title={t("conversations.transcript")}>
        <Transcript messages={messages} />
      </Card>
    </article>
  );
}

function ConversationHeader({
  conversation,
  messageCount,
  totals,
}: {
  conversation: ConversationSummaryView;
  messageCount: number;
  totals: ReturnType<typeof usageTotals>;
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
      <p className="sr-only">{tp("conversations.messages", messageCount)}</p>
    </Card>
  );
}
