/**
 * `quality.*` texts of production quality: the nightly judge's scores of
 * real conversations on the admin client page and on a conversation's
 * card, in English: the reference that ru and ka are typed against.
 */

export const qualityEn = {
  admin: {
    title: "Conversation quality, 30 days",
    description: "Each night an AI judge scores a small sample of real conversations on the five check criteria. Scores only, no customer text.",
    empty: "No conversations were judged in the last 30 days.",
    average: "Average, 30 days",
    lastWeek: "Last 7 days",
    previousWeek: "7 days before: {score}",
    judged: "Conversations judged",
    dropping: "Down {percent}%",
    droppingNote: "The last week scored {percent}% lower than the week before. Open the lowest conversations below and the client's latest update.",
    scoreValue: "{score} / 5",
    trendLabel: "Average score per day, last 30 days",
    noScoresDay: "{date}: not judged",
    dayValue: "{date}: {score} / 5 over {count}",
    showTable: "Show as a table",
    day: "Day",
    count: "Judged",
    lowestTitle: "Lowest-scored conversations",
    lowestCaption: "The five lowest scores of the 30 days",
    judgedAt: "Judged",
    channel: "Channel",
    language: "Language",
    score: "Score",
    weak: "Weak points",
    noWeak: "None below 4",
  },
  conversation: {
    title: "AI judge's score",
    description: "This conversation was in the nightly quality sample.",
    judgedAt: "Judged {date}",
    notes: "Notes",
  },
} as const;
