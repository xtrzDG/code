/** `assistantComparison.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { assistantComparisonEn } from "./assistantComparison.en";

export const assistantComparisonHe: Translation<typeof assistantComparisonEn> = {
  comparison: {
    title: "בהשוואה לעדכון {number} שבאוויר",
    description: "מושווים רק התרחישים ששני העדכונים שיחקו.",
    shared: "תרחישים שהושוו: {count}",
    averageScore: "ציון ממוצע",
    averageWas: "העדכון שבאוויר: {score}",
    newFailures: "בעיות חדשות",
    fixed: "תוקנו",
    newFailuresHint: "אלה עברו בעדכון שבאוויר ולא עוברים עכשיו.",
    fixedHint: "אלה לא עברו בעדכון שבאוויר ועוברים עכשיו.",
    scoreDrops: "ציונים שירדו",
    scoreRises: "ציונים שעלו",
    criteria: "לפי קריטריון",
    scenario: "{name} · {language}",
    scoreMove: "{from} ← {to}",
    outcomeMove: "{from} לפני, {to} עכשיו",
    noChanges: "שום דבר לא השתנה לעומת העדכון שבאוויר: אין בעיות חדשות, ואף ציון לא זז בחצי נקודה או יותר.",
    noShared: "להרצה הזו ולהרצה של העדכון שבאוויר עדיין אין תרחישים משותפים.",
    plays: "{passed} מתוך {played} משחקים עברו",
    playsHint: "תרחישים חשובים משוחקים יותר מפעם אחת; כל משחק חייב לעבור.",
  },
};
