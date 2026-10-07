/**
 * Pure rules of the Overview card "What customers ask about": which
 * language group is shown, how large each topic is in it, and whether a
 * topic waits for an answer.
 */

import type { Schema } from "@/api/types";

export type ConversationTopics = Schema<"ConversationTopicsView">;
export type TopicLanguageGroup = Schema<"TopicLanguageView">;
export type ConversationTopic = Schema<"ConversationTopicView">;

/** The key of the group of the languages beyond the largest ones (the API's `language: null`). */
export const OTHER_LANGUAGES = "other";

/** A group's key for the language switch: its language, or `OTHER_LANGUAGES`. */
export function topicGroupKey(group: TopicLanguageGroup): string {
  return group.language ?? OTHER_LANGUAGES;
}

/** Whether the topics were ever grouped (the first night has passed). */
export function wasGrouped(topics: ConversationTopics): boolean {
  return topics.window_to !== null && topics.window_to !== undefined;
}

/** The group with the key, else the largest one (the first); null without groups. */
export function chosenGroup(topics: ConversationTopics, key: string | null): TopicLanguageGroup | null {
  const groups = topics.groups ?? [];
  return groups.find((group) => topicGroupKey(group) === key) ?? groups[0] ?? null;
}

/** A topic's share of its group's conversations, in whole percent (for its bar). */
export function topicShare(topic: ConversationTopic, group: TopicLanguageGroup): number {
  return group.conversation_count === 0 ? 0 : Math.round((topic.conversation_count / group.conversation_count) * 100);
}

/** Whether a topic has open questions the assistant could not answer. */
export function needsAnswer(topic: ConversationTopic): boolean {
  return topic.unanswered_count > 0;
}

/**
 * A topic as the card names it: the catch-all of other questions in the
 * cabinet's own words (`otherTopic`), a named topic by its label (the API
 * already labels it in the cabinet's language).
 */
export function topicName(topic: ConversationTopic, otherTopic: string): string {
  return topic.kind === "other" ? otherTopic : topic.label;
}

/** A topic's key in its group (a named topic and the catch-all never clash). */
export function topicKey(topic: ConversationTopic): string {
  return `${topic.kind}:${topic.label}`;
}
