import { describe, expect, it } from "vitest";

import {
  chosenGroup,
  needsAnswer,
  OTHER_LANGUAGES,
  topicGroupKey,
  topicShare,
  wasGrouped,
  type ConversationTopics,
  type TopicLanguageGroup,
} from "./topicsModel";

const russian: TopicLanguageGroup = {
  language: "ru",
  conversation_count: 8,
  topics: [
    { label: "Бронирование", conversation_count: 5, unanswered_count: 0 },
    { label: "Парковка", conversation_count: 3, unanswered_count: 2 },
  ],
};
const others: TopicLanguageGroup = { language: null, conversation_count: 2, topics: [] };

function topics(groups: TopicLanguageGroup[], windowTo: number | null = 1_790_000_000_000_000): ConversationTopics {
  return { business_id: "biz_1", label_language: "ru", window_from: windowTo, window_to: windowTo, groups };
}

describe("topics model", () => {
  it("keys groups by language, the rest as other languages", () => {
    expect(topicGroupKey(russian)).toBe("ru");
    expect(topicGroupKey(others)).toBe(OTHER_LANGUAGES);
  });

  it("shows the chosen group, else the largest", () => {
    const view = topics([russian, others]);

    expect(chosenGroup(view, OTHER_LANGUAGES)).toBe(others);
    expect(chosenGroup(view, "ka")).toBe(russian);
    expect(chosenGroup(view, null)).toBe(russian);
    expect(chosenGroup(topics([]), null)).toBeNull();
  });

  it("tells grouped topics from the first night still to come", () => {
    expect(wasGrouped(topics([]))).toBe(true);
    expect(wasGrouped(topics([], null))).toBe(false);
  });

  it("sizes topics within their group and marks the unanswered", () => {
    const [booking, parking] = russian.topics ?? [];

    expect(topicShare(booking!, russian)).toBe(63);
    expect(topicShare(booking!, { ...russian, conversation_count: 0 })).toBe(0);
    expect(needsAnswer(booking!)).toBe(false);
    expect(needsAnswer(parking!)).toBe(true);
  });
});
