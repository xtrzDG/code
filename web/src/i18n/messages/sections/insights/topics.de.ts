/** `topics.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { topicsEn } from "./topics.en";

export const topicsDe: Translation<typeof topicsEn> = {
  title: "Wonach Kunden fragen",
  description: "Die ersten Nachrichten der letzten 30 Tage, jede Nacht nach Themen gruppiert.",
  updated: "Gruppiert am {date}",
  waiting: "Themen erscheinen nach der ersten Nacht mit Gesprächen.",
  empty: "In den letzten 30 Tagen hat noch kein Kunde geschrieben.",
  conversations: { one: "{count} Gespräch", other: "{count} Gespräche" },
  unanswered: { one: "{count} unbeantwortet", other: "{count} unbeantwortet" },
  unansweredHint: "Fragen, die der Assistent nicht beantworten konnte: Fügen Sie eine Antwort hinzu, dann tut er es.",
  addAnswer: "Antwort hinzufügen",
  otherLanguages: "Andere Sprachen",
  otherTopic: "Andere Fragen",
  languageLabel: "Sprache",
  loading: "Die Themen werden geladen…",
};
