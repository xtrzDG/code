"use client";

import Link from "next/link";
import { useState } from "react";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconBook } from "@/components/icons";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import { Badge, Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import {
  chosenGroup,
  needsAnswer,
  OTHER_LANGUAGES,
  topicGroupKey,
  topicKey,
  topicName,
  topicShare,
  wasGrouped,
  type ConversationTopic,
  type TopicLanguageGroup,
} from "@/components/value/topicsModel";
import { useConversationTopics } from "@/components/value/useValueQueries";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

/**
 * "What customers ask about" (Overview, owners and staff): the first
 * messages of the last 30 days grouped into topics every night, per
 * customer language, labelled in the cabinet's language (the catch-all of
 * other questions in the cabinet's own words). A topic with questions the
 * assistant could not answer links owners to them ("Add an answer").
 */
export function TopicsCard() {
  const { t, locale } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const topics = useConversationTopics(business.id, locale);
  const [language, setLanguage] = useState<string | null>(null);
  const questionsHref = `${businessPath(business.id, "assistant/knowledge")}/questions`;

  const view = topics.data;
  const groups = view?.groups ?? [];
  const group = view ? chosenGroup(view, language) : null;
  const hasUnanswered = groups.some((item) => (item.topics ?? []).some(needsAnswer));

  return (
    <Card
      aria-label={t("topics.title")}
      title={t("topics.title")}
      description={t("topics.description")}
      actions={
        groups.length > 1 && group ? (
          <SegmentedControl
            label={t("topics.languageLabel")}
            value={topicGroupKey(group)}
            onChange={setLanguage}
            options={groups.map((item) => ({ value: topicGroupKey(item), label: groupName(item) }))}
          />
        ) : undefined
      }
    >
      {topics.error && !view ? (
        <ErrorState error={topics.error} onRetry={topics.reload} />
      ) : !view ? (
        <LoadingRegion label={t("topics.loading")}>
          <SkeletonText lines={4} />
        </LoadingRegion>
      ) : !wasGrouped(view) ? (
        <p className="py-4 text-center text-sm text-ink-muted">{t("topics.waiting")}</p>
      ) : !group || (group.topics ?? []).length === 0 ? (
        <p className="py-4 text-center text-sm text-ink-muted">{t("topics.empty")}</p>
      ) : (
        <div className="space-y-4">
          <ul className="space-y-3.5">
            {(group.topics ?? []).map((topic) => (
              <TopicRow key={topicKey(topic)} topic={topic} group={group} questionsHref={isOwner ? questionsHref : null} />
            ))}
          </ul>
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-subtle">
            {isOwner && hasUnanswered ? (
              <p className="flex items-center gap-1.5">
                <IconBook className="size-3.5 shrink-0" aria-hidden />
                {t("topics.unansweredHint")}
              </p>
            ) : null}
            {view.window_to ? <p className="ms-auto">{t("topics.updated", { date: format.date(view.window_to) })}</p> : null}
          </div>
        </div>
      )}
    </Card>
  );

  function groupName(item: TopicLanguageGroup): string {
    const key = topicGroupKey(item);
    return key === OTHER_LANGUAGES ? t("topics.otherLanguages") : languageName(key, locale);
  }
}

/** One topic: its label, how many conversations opened with it (a bar), and what waits for an answer. */
function TopicRow({
  topic,
  group,
  questionsHref,
}: {
  topic: ConversationTopic;
  group: TopicLanguageGroup;
  /** Owners: the questions to answer; null for staff. */
  questionsHref: string | null;
}) {
  const { t, tp } = useI18n();
  const share = topicShare(topic, group);
  const name = topicName(topic, t("topics.otherTopic"));
  return (
    <li>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="min-w-0 font-medium break-words text-ink" data-topic-kind={topic.kind}>
          {name}
        </span>
        <span className="shrink-0 text-ink-muted tabular-nums">{tp("topics.conversations", topic.conversation_count)}</span>
      </div>
      <div className="mt-1.5 h-2 rounded-full bg-surface-muted" aria-hidden>
        <div className="h-full rounded-full bg-accent-solid" style={{ width: `${Math.max(share, 2)}%` }} />
      </div>
      {needsAnswer(topic) ? (
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
          <Badge tone="warning">{tp("topics.unanswered", topic.unanswered_count)}</Badge>
          {questionsHref ? (
            <Link
              href={questionsHref}
              className="rounded text-sm font-medium text-accent-ink underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              {t("topics.addAnswer")}
              <span className="sr-only">{`: ${name}`}</span>
            </Link>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}
