"use client";

/**
 * Everything about the conversation that is not the conversation itself,
 * folded away from the transcript: the customer and how to reach them,
 * when it started, how the assistant did, what came out of it (bookings,
 * requests, handoffs), the calls with their recordings, and the
 * technical details.
 */

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { AfterHoursBadge, ChannelBadge, ConversationStatusBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName, DetailRow, PhoneLink } from "@/components/insights/common";
import type { ConversationDetailView } from "@/components/insights/types";
import { useI18n } from "@/i18n/client";
import { RatingReasons } from "@/components/teaching/RatingReasons";
import { languageName } from "@/lib/format";
import { latestAnswerId } from "@/lib/teaching";

import { fromUsage, usageTotals } from "../../_lib/conversationUsage";
import { useConversationRating } from "../../_lib/useConversationRating";
import { ConversationTechnicalDetails } from "../conversation/TechnicalDetails";
import { CallsCard } from "./CallsCard";
import { LinkedItems } from "./LinkedItems";
import { RatingControl } from "./RatingControl";

export function DetailsPanel({
  detail,
  onBook,
  onFixAnswer,
  onSaveCheck,
}: {
  detail: ConversationDetailView;
  onBook: (() => void) | null;
  /** Owners: "Fix this answer" on an assistant answer (null: not offered). */
  onFixAnswer: ((messageId: string) => void) | null;
  /** Owners: "Save as a check" from the conversation's bad rating. */
  onSaveCheck: ((messageId: string | null) => void) | null;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const { conversation } = detail;
  const rate = useConversationRating(conversation.id);
  const ratedAnswer = conversation.rated_message_id ?? latestAnswerId(detail.messages ?? []);
  const totals = detail.usage ? fromUsage(detail.usage) : usageTotals(detail.messages ?? []);

  return (
    <div className="space-y-5">
      <section aria-label={t("inboxCard.details.customer")} className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-base font-semibold text-ink">
            <CustomerName name={conversation.contact_name} />
          </p>
          <ConversationStatusBadge status={conversation.status} />
          {conversation.is_after_hours ? <AfterHoursBadge /> : null}
          {conversation.is_sandbox ? <TestBadge /> : null}
        </div>
        <dl className="divide-y divide-line rounded-2xl border border-line bg-surface px-4">
          <DetailRow label={t("inboxCard.details.customer")}>
            {conversation.contact_phone_number ? (
              <PhoneLink phone={conversation.contact_phone_number} />
            ) : (
              <span className="text-ink-muted">{t("conversations.noPhone")}</span>
            )}
          </DetailRow>
          <DetailRow label={t("inboxCard.details.channel")}>
            <ChannelBadge channel={conversation.channel} />
          </DetailRow>
          {conversation.language ? (
            <DetailRow label={t("inboxCard.details.language")}>{languageName(conversation.language, locale)}</DetailRow>
          ) : null}
          <DetailRow label={t("inboxCard.details.started")}>{format.dateTime(conversation.created_at)}</DetailRow>
          <DetailRow label={t("inboxCard.details.lastMessage")}>{format.dateTime(conversation.last_message_at)}</DetailRow>
        </dl>
      </section>

      <div className="rounded-2xl border border-line bg-surface px-4 py-3">
        <RatingControl
          value={conversation.rating ?? null}
          isPending={rate.isPending}
          onChange={(rating) => void rate.change(rating)}
        />
        {conversation.rating === "bad" ? (
          <RatingReasons
            value={conversation.rating_reason ?? null}
            isPending={rate.isPending}
            onChange={(reason) => void rate.change("bad", reason)}
            onFix={onFixAnswer && ratedAnswer ? () => onFixAnswer(ratedAnswer) : null}
            onSaveCheck={onSaveCheck ? () => onSaveCheck(ratedAnswer) : null}
          />
        ) : null}
      </div>

      <LinkedItems detail={detail} onBook={onBook} />

      {(detail.calls ?? []).length > 0 ? <CallsCard calls={detail.calls ?? []} /> : null}

      <ConversationTechnicalDetails totals={totals} versionId={conversation.assistant_version_id} />
    </div>
  );
}
