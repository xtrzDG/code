"use client";

/**
 * "Answers worth improving" (Overview, owners and staff): conversations
 * rated bad that nobody acted on yet, then the questions the assistant
 * could not answer. Owners fix an answer or keep the question as a check
 * right here; everyone can open the conversation.
 */

import Link from "next/link";
import { useState } from "react";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge, Button, Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath, conversationPath } from "@/lib/navigation";
import { REASON_LABELS, type AnswerToImprove } from "@/lib/teaching";
import { checkFormFromItem, type CheckForm } from "@/lib/teachingChecks";

import { AnswerFixDialog } from "./AnswerFixDialog";
import { CheckDialog } from "./CheckDialog";
import { useAnswersToImprove } from "./useTeaching";

const LINK = "rounded text-sm font-medium text-accent-ink underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus";

export function AnswersToImproveCard() {
  const { t, tp } = useI18n();
  const { business, isOwner } = useBusiness();
  const answers = useAnswersToImprove();
  const [fixing, setFixing] = useState<{ conversationId: string; messageId: string } | null>(null);
  const [check, setCheck] = useState<CheckForm | null>(null);
  const view = answers.data;
  const items = view?.items ?? [];
  const waiting = view ? view.bad_rating_count + view.unanswered_count : 0;

  return (
    <Card aria-label={t("teaching.improve.title")} title={t("teaching.improve.title")} description={t("teaching.improve.description")}>
      {answers.error && !view ? (
        <ErrorState error={answers.error} onRetry={answers.reload} />
      ) : !view ? (
        <LoadingRegion label={t("teaching.improve.loading")}>
          <SkeletonText lines={4} />
        </LoadingRegion>
      ) : items.length === 0 ? (
        <p className="py-4 text-center text-sm text-ink-muted">{t("teaching.improve.empty")}</p>
      ) : (
        <div className="space-y-3">
          <ul className="divide-y divide-line" data-answers-to-improve="">
            {items.map((item) => (
              <ImproveRow
                key={item.question_id ?? item.conversation_id ?? item.at}
                item={item}
                isOwner={isOwner}
                onFix={(conversationId, messageId) => setFixing({ conversationId, messageId })}
                onSaveCheck={() => setCheck(checkFormFromItem(item, business.default_language))}
              />
            ))}
          </ul>
          {waiting > items.length ? (
            <p className="text-xs text-ink-subtle">
              {t("teaching.improve.more", {
                ratings: tp("teaching.improve.moreRatings", view.bad_rating_count),
                questions: tp("teaching.improve.moreQuestions", view.unanswered_count),
              })}
            </p>
          ) : null}
        </div>
      )}
      <AnswerFixDialog conversationId={fixing?.conversationId ?? ""} messageId={fixing?.messageId ?? null} onClose={() => setFixing(null)} />
      {check ? (
        <CheckDialog
          open
          initial={check}
          check={null}
          title={t("teaching.checks.saveTitle")}
          description={t("teaching.checks.saveDescription")}
          onClose={() => setCheck(null)}
        />
      ) : null}
    </Card>
  );
}

function ImproveRow({
  item,
  isOwner,
  onFix,
  onSaveCheck,
}: {
  item: AnswerToImprove;
  isOwner: boolean;
  onFix: (conversationId: string, messageId: string) => void;
  onSaveCheck: () => void;
}) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  const isQuestion = item.kind === "unanswered_question";
  const conversationId = item.conversation_id ?? null;
  const messageId = item.message_id ?? null;

  return (
    <li className="space-y-2 py-3 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2 text-xs text-ink-subtle">
        <Badge tone={isQuestion ? "warning" : "danger"}>
          {isQuestion ? t("teaching.improve.unanswered") : t("teaching.improve.badRating")}
        </Badge>
        {item.rating_reason ? <span>{t(REASON_LABELS[item.rating_reason])}</span> : null}
        {isQuestion && item.occurrence_count ? <span>{tp("teaching.improve.asked", item.occurrence_count)}</span> : null}
        <span className="ms-auto">{format.dateTime(item.at)}</span>
      </div>
      {isQuestion ? (
        <p dir="auto" data-user-content className="text-sm font-medium break-words text-ink">
          {item.question}
        </p>
      ) : (
        <dl className="space-y-1 text-sm">
          {item.customer_message ? (
            <div className="flex gap-2">
              <dt className="shrink-0 text-ink-subtle">{t("teaching.improve.customer")}:</dt>
              <dd dir="auto" data-user-content className="min-w-0 break-words text-ink">
                {item.customer_message}
              </dd>
            </div>
          ) : null}
          {item.answer ? (
            <div className="flex gap-2">
              <dt className="shrink-0 text-ink-subtle">{t("teaching.improve.assistant")}:</dt>
              <dd dir="auto" data-user-content className="line-clamp-2 min-w-0 break-words text-ink-muted">
                {item.answer}
              </dd>
            </div>
          ) : null}
        </dl>
      )}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {isOwner && !isQuestion && conversationId && messageId ? (
          <Button size="sm" onClick={() => onFix(conversationId, messageId)}>
            {t("teaching.improve.fix")}
          </Button>
        ) : null}
        {isOwner && isQuestion ? (
          <Link href={`${businessPath(business.id, "assistant/knowledge")}/questions`} className={LINK}>
            {t("teaching.improve.addAnswer")}
          </Link>
        ) : null}
        {isOwner ? (
          <button type="button" onClick={onSaveCheck} className={LINK}>
            {t("teaching.improve.saveCheck")}
          </button>
        ) : null}
        {conversationId ? (
          <Link href={conversationPath(business.id, conversationId)} className={LINK}>
            {t("teaching.improve.open")}
          </Link>
        ) : null}
      </div>
    </li>
  );
}
