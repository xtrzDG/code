"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { formatScore, JUDGE_CRITERIA, scoreTone, type JudgeCriterion } from "@/lib/assistant/autotests";

const CRITERION_LABELS: Record<JudgeCriterion, MessageKey> = {
  facts_and_prices: "assistant.autotests.criteria.facts_and_prices",
  booking_data: "assistant.autotests.criteria.booking_data",
  ai_disclosure: "assistant.autotests.criteria.ai_disclosure",
  handoff: "assistant.autotests.criteria.handoff",
  language: "assistant.autotests.criteria.language",
};

/**
 * The nightly judge's score of this conversation, when the quality sample
 * picked it (most conversations it did not, and then nothing shows): the
 * average, the five criteria and the judge's notes.
 */
export function QualityScore({ conversationId }: { conversationId: string }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const quality = useQuery(queryKeys.conversations.quality(business.id, conversationId), () =>
    api.GET("/v1/businesses/{business_id}/conversations/{conversation_id}/quality", {
      params: { path: { business_id: business.id, conversation_id: conversationId } },
    }),
  );
  const score = quality.data?.score;
  if (!score) {
    return null;
  }

  const notes = score.judge_notes ?? [];
  return (
    <section data-quality-score aria-labelledby={`quality-${conversationId}`} className="space-y-3 rounded-2xl border border-line bg-surface px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 id={`quality-${conversationId}`} className="text-sm font-semibold text-ink">
            {t("quality.conversation.title")}
          </h3>
          <p className="text-xs text-ink-subtle">
            {t("quality.conversation.description")} {t("quality.conversation.judgedAt", { date: format.date(score.judged_at) })}
          </p>
        </div>
        <Badge tone={scoreTone(score.average_score)}>{t("assistant.autotests.scoreValue", { score: formatScore(score.average_score, locale) })}</Badge>
      </div>
      <ul className="grid grid-cols-1 gap-1.5 text-sm sm:grid-cols-2">
        {JUDGE_CRITERIA.map((criterion) => {
          const value = score.scores.find((item) => item.criterion === criterion)?.score;
          return (
            <li key={criterion} className="flex items-center justify-between gap-2 rounded-lg bg-surface-muted px-3 py-1.5">
              <span className="text-ink-muted">{t(CRITERION_LABELS[criterion])}</span>
              {value !== undefined ? (
                <Badge tone={scoreTone(value)}>{t("assistant.autotests.criterionScore", { score: value })}</Badge>
              ) : (
                <span className="text-ink-subtle">—</span>
              )}
            </li>
          );
        })}
      </ul>
      {notes.length > 0 ? (
        <div>
          <h4 className="mb-1 text-xs font-semibold tracking-wide text-ink-muted uppercase">{t("quality.conversation.notes")}</h4>
          <ul className="list-disc space-y-0.5 pl-5 text-sm text-ink-muted">
            {notes.map((note, index) => (
              <li key={index} dir="auto">
                {note}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
