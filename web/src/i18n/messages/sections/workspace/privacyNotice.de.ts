/** `privacyNotice.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { privacyNoticeEn } from "./privacyNotice.en";

export const privacyNoticeDe: Translation<typeof privacyNoticeEn> = {
  title: "Datenschutzhinweis",
  subtitle: "Wie {business} mit dem umgeht, was Sie in den Chat schreiben",
  whoTitle: "Wer antwortet",
  who: "{business} beantwortet Nachrichten mit einem KI-Assistenten – auf der Website, auf dieser Seite und in Messengern. Assistant Workshop stellt den Assistenten bereit und verarbeitet Ihre Nachrichten im Auftrag von {business}; {business} entscheidet, was mit ihnen geschieht.",
  whatTitle: "Was gespeichert wird",
  whatMessages: "Was Sie in den Chat schreiben, und die Antworten des Assistenten.",
  whatContacts: "Ihr Name, Ihre Telefonnummer oder E-Mail-Adresse, wenn Sie sie angeben (zum Beispiel für eine Buchung oder einen Rückruf).",
  whatBrowser: "Ein zufälliger Schlüssel im Speicher Ihres Browsers, damit der Chat dort weitergeht, wo Sie aufgehört haben. Der Chat setzt keine Cookies.",
  whatTechnical: "Technische Daten wie Ihre IP-Adresse, für kurze Zeit gespeichert, um den Chat vor Missbrauch zu schützen.",
  whyTitle: "Wozu",
  why: "Um Ihre Fragen zu beantworten, Buchungen und Anfragen aufzunehmen und das Gespräch an die Mitarbeitenden von {business} weiterzugeben, wenn Sie eine Person sprechen möchten oder der Assistent nicht helfen kann.",
  sharedTitle: "Wer es sieht",
  shared: "Die Mitarbeitenden von {business}. Um Antworten zu schreiben, wird der Text des Gesprächs vom Anbieter des KI-Modells verarbeitet, auf dem der Assistent läuft – nur zu diesem Zweck.",
  keptTitle: "Wie lange",
  kept: "{business} speichert Gespräche {conversations} nach ihrer letzten Nachricht, danach werden sie automatisch gelöscht, und die Aufzeichnungen der KI-Aufrufe des Assistenten {modelRecords}. Sie können jederzeit verlangen, dass Ihres gelöscht wird.",
  rightsTitle: "Ihre Möglichkeiten",
  rights: "Sie können {business} fragen, was über Sie gespeichert ist, und die Berichtigung oder Löschung verlangen: Schreiben Sie in den Chat oder wenden Sie sich direkt an das Unternehmen. Der Assistent kann sich irren – prüfen Sie wichtige Angaben (Preise, Zeiten) beim Unternehmen.",
  platformNote: "Dies ist der Standardhinweis der Plattform Assistant Workshop. {business} kann einen eigenen veröffentlichen.",
  backToChat: "Zurück zum Chat",
};
