/** `helpCenter.*` in German: the help center and the support panel (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { helpCenterEn } from "./helpCenter.en";

export const helpCenterDe: Translation<typeof helpCenterEn> = {
  title: "Hilfe",
  description: "Kurze Anleitungen zu jedem Teil des Dashboards.",
  searchLabel: "Hilfe durchsuchen",
  searchPlaceholder: "Telegram, Buchung, Rechnung…",
  search: "Suchen",
  clearSearch: "Suche löschen",
  results: {
    one: "{count} Artikel gefunden",
    other: "{count} Artikel gefunden",
  },
  noResults: "Nichts gefunden für „{query}“. Versuchen Sie ein anderes Wort.",
  topics: {
    getting_started: "Erste Schritte",
    channels: "Kanäle",
    daily_work: "Tägliche Arbeit",
    account: "Konto und Abrechnung",
  },
  loadFailed: "Die Hilfe konnte nicht geladen werden. Prüfen Sie die Verbindung und versuchen Sie es erneut.",
  allArticles: "Alle Artikel",
  related: "Weiterlesen",
  otherLanguage: "Dieser Artikel ist noch nicht übersetzt und wird deshalb auf {language} angezeigt.",
  pageHelp: "Hilfe zu dieser Seite",
  drawerTitle: "Hilfe",
  openInCenter: "Im Hilfe-Center öffnen",
  back: "Zurück",
  stillStuck: "Kommen Sie nicht weiter?",
  stillStuckLead: "Schreiben Sie uns: Eine Person aus dem Team antwortet.",
  noSupportLead: "Prüfen Sie den Plattformstatus: Wenn etwas bei allen nicht funktioniert, arbeitet das Team bereits daran.",
  tipsAgain: "Tipps wieder anzeigen",
  tipsShown: "Die Tipps erscheinen wieder auf den Seiten Posteingang, Assistent und Kanäle.",
  opensInNewTab: "öffnet sich in einem neuen Tab",
  support: {
    title: "Hilfe und Support",
    center: "Hilfe-Center",
    whatsNew: "Neuigkeiten",
    unread: {
      one: "{count} neu",
      other: "{count} neu",
    },
    status: "Plattformstatus",
    contact: "Support anschreiben",
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    email: "E-Mail",
  },
};
