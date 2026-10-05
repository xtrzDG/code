/**
 * `assistant.comparison.*` texts: an update's checks against the live
 * update's, in English: the reference that ru and ka are typed against.
 */

export const assistantComparisonEn = {
  comparison: {
    title: "Compared with the live update {number}",
    description: "Only the scenarios both updates played are compared.",
    shared: "Scenarios compared: {count}",
    averageScore: "Average score",
    averageWas: "Live update: {score}",
    newFailures: "New problems",
    fixed: "Fixed",
    newFailuresHint: "These passed on the live update and do not pass now.",
    fixedHint: "These did not pass on the live update and pass now.",
    scoreDrops: "Scores that fell",
    scoreRises: "Scores that rose",
    criteria: "By criterion",
    scenario: "{name} · {language}",
    scoreMove: "{from} → {to}",
    outcomeMove: "{from} before, {to} now",
    noChanges: "Nothing changed against the live update: no new problems, and no score moved by half a point or more.",
    noShared: "This run and the live update's run have no scenarios in common yet.",
    plays: "{passed} of {played} plays passed",
    playsHint: "Important scenarios are played more than once; each play must pass.",
  },
} as const;
