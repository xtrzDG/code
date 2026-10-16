/** `assistantComparison.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { assistantComparisonEn } from "./assistantComparison.en";

export const assistantComparisonDe: Translation<typeof assistantComparisonEn> = {
  comparison: {
    title: "Verglichen mit dem Live-Update {number}",
    description: "Verglichen werden nur die Szenarien, die beide Updates gespielt haben.",
    shared: "Verglichene Szenarien: {count}",
    averageScore: "Durchschnittliche Bewertung",
    averageWas: "Live-Update: {score}",
    newFailures: "Neue Probleme",
    fixed: "Behoben",
    newFailuresHint: "Diese haben beim Live-Update bestanden und bestehen jetzt nicht.",
    fixedHint: "Diese haben beim Live-Update nicht bestanden und bestehen jetzt.",
    scoreDrops: "Gesunkene Bewertungen",
    scoreRises: "Gestiegene Bewertungen",
    criteria: "Nach Kriterium",
    scenario: "{name} · {language}",
    scoreMove: "{from} → {to}",
    outcomeMove: "vorher {from}, jetzt {to}",
    noChanges: "Gegenüber dem Live-Update hat sich nichts geändert: keine neuen Probleme, und keine Bewertung hat sich um einen halben Punkt oder mehr bewegt.",
    noShared: "Dieser Durchlauf und der des Live-Updates haben noch keine gemeinsamen Szenarien.",
    plays: { one: "{passed} von {played} Durchgang bestanden", other: "{passed} von {played} Durchgängen bestanden" },
    playsHint: "Wichtige Szenarien werden mehrmals gespielt; jeder Durchgang muss bestehen.",
  },
};
