/** `insightsCommon.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { insightsCommonEn } from "./common.en";

export const insightsCommonDe: Translation<typeof insightsCommonEn> = {
  loadingMore: "Wird geladen…",
  showMore: "Mehr anzeigen",
  shownOf: "{shown} von {total} angezeigt",
  includeTest: "Testaktivität einbeziehen",
  includeTestHint: "Aus dem Test-Chat und den Prüfungen",
  testBadge: "Test",
  afterHours: "Außerhalb der Zeiten",
  unknownCustomer: "Kunde ohne Namen",
  callPhone: "{phone} anrufen",
  openConversation: "Gespräch öffnen",
  all: "Alle",
  clearFilters: "Filter zurücksetzen",
  noMatchesTitle: "Nichts passt zu den Filtern",
  noMatchesDescription: "Ändern oder löschen Sie die Filter, um mehr zu sehen.",
  copy: "Kopieren",
  copied: "In die Zwischenablage kopiert",
  copyFailed: "Kopieren nicht möglich. Markieren Sie den Text und kopieren Sie ihn von Hand.",
  customerMessage: {
    title: "Nachricht an den Kunden",
    description: "Hier sendet der Assistent diesen Text nicht selbst. Senden Sie ihn dem Kunden in dem Kanal, in dem Sie sprechen.",
  },
  channels: {
    phone: "Telefon",
    whatsapp: "WhatsApp",
    instagram: "Instagram",
    messenger: "Messenger",
    telegram: "Telegram",
    web_chat: "Website-Chat",
    viber: "Viber",
    owner_test: "Test-Chat",
  },
};
