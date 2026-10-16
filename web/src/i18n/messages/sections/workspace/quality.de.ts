/** `quality.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { qualityEn } from "./quality.en";

export const qualityDe: Translation<typeof qualityEn> = {
  admin: {
    title: "Gesprächsqualität, 30 Tage",
    description: "Jede Nacht bewertet ein KI-Richter eine kleine Stichprobe echter Gespräche nach den fünf Prüfkriterien. Nur Bewertungen, kein Kundentext.",
    empty: "In den letzten 30 Tagen wurden keine Gespräche bewertet.",
    average: "Durchschnitt, 30 Tage",
    lastWeek: "Letzte 7 Tage",
    previousWeek: "7 Tage davor: {score}",
    judged: "Bewertete Gespräche",
    dropping: "Minus {percent} %",
    droppingNote: "Die letzte Woche wurde {percent} % schlechter bewertet als die Woche davor. Öffnen Sie unten die am schlechtesten bewerteten Gespräche und das letzte Update des Kunden.",
    scoreValue: "{score} / 5",
    trendLabel: "Durchschnittliche Bewertung pro Tag, letzte 30 Tage",
    noScoresDay: "{date}: nicht bewertet",
    dayValue: "{date}: {score} / 5 über {count}",
    showTable: "Als Tabelle anzeigen",
    day: "Tag",
    count: "Bewertet",
    lowestTitle: "Am schlechtesten bewertete Gespräche",
    lowestCaption: "Die fünf niedrigsten Bewertungen der 30 Tage",
    judgedAt: "Bewertet",
    channel: "Kanal",
    language: "Sprache",
    score: "Bewertung",
    weak: "Schwachstellen",
    noWeak: "Keine unter 4",
  },
  conversation: {
    title: "Bewertung des KI-Richters",
    description: "Dieses Gespräch war in der nächtlichen Qualitätsstichprobe.",
    judgedAt: "Bewertet {date}",
    notes: "Notizen",
  },
};
