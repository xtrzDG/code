/** `privacyRetention.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { privacyRetentionEn } from "./privacyRetention.en";

export const privacyRetentionDe: Translation<typeof privacyRetentionEn> = {
  title: "Wie lange Daten aufbewahrt werden",
  description: "Kundendaten werden automatisch gelöscht, sobald diese Fristen verstrichen sind. Der Datenschutzhinweis Ihres Chats nennt Kunden dieselben Fristen.",
  conversations: {
    label: "Gespräche",
    hint: "Gezählt ab der letzten Nachricht eines Gesprächs. Danach werden seine Nachrichten, die Notizen des Teams, Anruftranskripte und Aufnahmen gelöscht; Buchungen und Anfragen behalten nur, was nicht personenbezogen ist.",
  },
  modelRecords: {
    label: "Aufzeichnungen der KI-Aufrufe des Assistenten",
    hint: "Der genaue Text, der an das KI-Modell ging, aufbewahrt zur Prüfung von Antworten. Wird hier und im Qualitätsjournal (Langfuse) gelöscht. Höchstens 30 Tage.",
  },
  periods: {
    days: { one: "{count} Tag", other: "{count} Tage" },
    months: { one: "{count} Monat", other: "{count} Monate" },
    years: { one: "{count} Jahr", other: "{count} Jahre" },
    recommended: "{period} (empfohlen)",
    maximum: "{period} (Maximum)",
  },
  recordings: "Anrufaufnahmen werden {period} aufbewahrt.",
  changeRecordings: "Unter Allgemein ändern",
  processorsTitle: "Kopien bei unseren Unterauftragsverarbeitern",
  processors: {
    langfuse: "Langfuse: Protokolle der KI-Aufrufe des Assistenten",
    elevenlabs: "ElevenLabs: Anrufe (Audio und Transkript)",
  },
  processorsDeleted: "werden zusammen mit unseren gelöscht, nach diesen Fristen und wenn Sie die Daten eines Kunden löschen:",
  processorsNone: "Langfuse und ElevenLabs werden auf dieser Plattform nicht verwendet, daher bewahren sie keine Kopien der Daten Ihrer Kunden auf.",
  messagingApps: "Chats in WhatsApp, Messenger, Instagram und Telegram bleiben in der App des Kunden: Diese Plattformen lassen nur den Kunden sie löschen.",
  lastCleanupTitle: "Letzte Bereinigung",
  lastCleanup: "{date}",
  nothingDue: "Es war nichts zu löschen.",
  noCleanupYet: "Die erste Bereinigung läuft heute Nacht.",
  removed: { one: "{count} Datensatz entfernt", other: "{count} Datensätze entfernt" },
  counts: {
    deleted_messages: "Nachrichten",
    deleted_llm_turns: "Aufzeichnungen von KI-Aufrufen",
    deleted_notes: "Team-Notizen",
    deleted_media: "Dateien von Kunden",
    deleted_missed_calls: "verpasste Anrufe",
    erased_calls: "Anrufe",
    anonymized_leads: "Anfragen",
    anonymized_bookings: "Buchungen",
    anonymized_handoffs: "Übergaben",
  },
  shorterTitle: "Ältere Daten heute Nacht löschen?",
  shorterDescription:
    "Mit kürzeren Fristen löscht die Bereinigung heute Nacht endgültig alles, was darüber hinausgeht (Gespräche: {conversations}; Aufzeichnungen von KI-Aufrufen: {modelRecords}). Das lässt sich nicht rückgängig machen.",
  shorterConfirm: "Verkürzen und löschen",
  qualitySampling: {
    label: "Qualitätsprüfungen echter Gespräche",
    hint: "Jede Nacht wird eine kleine Stichprobe abgeschlossener Gespräche (ohne Test-Chats) vom selben KI-Anbieter bewertet, der die Antworten schreibt, damit schwache Antworten in der Qualität des Assistenten sichtbar werden. Schalten Sie es aus, um die Gespräche Ihrer Kunden aus diesen Prüfungen herauszuhalten.",
  },
};
