/** `inboxCard.*` in German: the conversation card in the inbox (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { inboxCardEn } from "./inboxCard.en";

export const inboxCardDe: Translation<typeof inboxCardEn> = {
  back: "Zurück zum Posteingang",
  openDetails: "Details",
  openDetailsOf: "Details des Gesprächs mit {name}",
  openNotes: "Notizen",
  openNotesCount: {
    one: "Notizen ({count})",
    other: "Notizen ({count})",
  },
  panelLabel: "Über dieses Gespräch",
  panelTabs: "Bereich",
  messageContext: {
    story_reply: "Antwort auf Ihre Story",
    story_mention: "Erwähnung in der Story des Kunden",
  },
  offeredChoices: "Angebotene Auswahl",
  actions: {
    label: "Schnellaktionen",
    resolve: "Erledigen",
    resolveHint: "Der Assistent antwortet diesem Kunden wieder",
    call: "Anrufen",
    callLabel: "{phone} anrufen",
    book: "Buchen",
  },
  work: {
    needsPerson: "Braucht eine Person",
    request: "Anfrage",
    requestStatus: "Status der Anfrage",
    since: "seit {time}",
  },
  details: {
    customer: "Kunde",
    channel: "Kanal",
    language: "Sprache",
    started: "Begonnen",
    lastMessage: "Letzte Nachricht",
  },
  technical: {
    title: "Technische Details",
    hint: "Was hinter den Antworten steht: das Update des Assistenten, das sie gegeben hat, und seine genauen Anfragen an Ihre Daten.",
    tokens: "Tokens",
    cost: "KI-Kosten",
    version: "Version des Assistenten",
    message: "Technische Details dieser Nachricht",
  },
  notes: {
    title: "Notizen",
    hint: "Nur Ihr Team sieht das",
    description: "Notizen bleiben in Ihrem Team: Kunde und Assistent sehen sie nie.",
    placeholder: "Was zugesagt wurde, wer zurückruft, woran zu denken ist…",
    add: "Notiz hinzufügen",
    adding: "Wird gespeichert…",
    added: "Notiz gespeichert. Nur Ihr Team sieht sie.",
    unknownAuthor: "Ehemaliges Teammitglied",
    delete: "Notiz löschen",
    confirmDelete: {
      title: "Diese Notiz löschen?",
      description: "Sie verschwindet für das ganze Team.",
      confirm: "Löschen",
    },
    deleted: "Notiz gelöscht",
    empty: "Noch keine Notizen. Eine Notiz hilft der nächsten Person: was zugesagt wurde, wer zurückruft.",
    loading: "Notizen werden geladen…",
    length: "{count} / {max}",
  },
  quickReplies: {
    open: "Schnellantworten",
    hint: "Tippen Sie / für Schnellantworten",
    listLabel: "Schnellantworten",
    loading: "Schnellantworten werden geladen…",
    empty: "Noch keine Schnellantworten.",
    emptyOwner: "Legen Sie häufige Antworten unter Einstellungen → Schnellantworten an.",
    manage: "Schnellantworten verwalten",
    noMatch: "Keine Schnellantwort passt zu „/{query}“.",
    missing: "Vor dem Senden ausfüllen:",
    fillLabel: "Wert für {variable}",
    fill: "Ausfüllen",
    placeholdersLeft: "Füllen Sie vor dem Senden die Teile in geschweiften Klammern aus: {variables}.",
    variables: {
      name: "Name des Kunden",
      booking_time: "Buchungszeit",
      business_name: "Name des Unternehmens",
    },
  },
  composer: {
    placeholder: "Dem Kunden schreiben…",
    sendLabel: "Senden",
  },
  request: {
    updated: "Anfrage: {status}",
  },
  resolveConfirm: {
    title: "Als erledigt markieren?",
    description: "{name}: Der Assistent antwortet diesem Kunden wieder.",
    confirm: "Erledigen",
  },
  resolved: "Als erledigt markiert. Der Assistent antwortet diesem Kunden wieder.",
  reopened: "Die Übergabe ist wieder offen. Der Assistent schweigt, bis sie erledigt ist.",
};
