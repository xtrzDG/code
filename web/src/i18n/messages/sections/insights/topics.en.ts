/**
 * `topics.*` texts: the Overview card "What customers ask about" (the first
 * messages of the last 30 days, grouped every night), in English: the
 * reference ru and ka are typed against.
 */

export const topicsEn = {
  title: "What customers ask about",
  description: "The first messages of the last 30 days, grouped into topics every night.",
  updated: "Grouped on {date}",
  waiting: "Topics appear after the first night with conversations.",
  empty: "No customer wrote in the last 30 days yet.",
  conversations: { one: "{count} conversation", other: "{count} conversations" },
  unanswered: { one: "{count} unanswered", other: "{count} unanswered" },
  unansweredHint: "Questions the assistant could not answer: add an answer and it will.",
  addAnswer: "Add an answer",
  otherLanguages: "Other languages",
  languageLabel: "Language",
  loading: "Loading the topics…",
} as const;
