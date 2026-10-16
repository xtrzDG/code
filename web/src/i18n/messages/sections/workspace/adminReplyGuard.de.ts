/** `adminReplyGuard.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminReplyGuardEn } from "./adminReplyGuard.en";

export const adminReplyGuardDe: Translation<typeof adminReplyGuardEn> = {
  title: "Antwortschutz, 7 Tage",
  description:
    "Antworten, die der Schutz zurückgehalten hat, weil Zahlen, Aussagen oder Kontaktdaten nicht durch die Daten des Unternehmens gedeckt waren, und Nachrichten, die die Anweisungen des Assistenten ändern wollten.",
  checked: "Geprüfte Antworten",
  heldBack: "Zurückgehalten",
  heldBackShare: "{share} der Antworten",
  rewritten: "Einmal umgeschrieben",
  handedOff: "An das Team gegeben",
  injectionFlags: "Injektionsversuche",
  heldBackNote:
    "Der Schutz hat mindestens jede sechste Antwort zurückgehalten. Prüfen Sie die Fakten und Preise des Unternehmens: Dem Assistenten fehlt etwas, wonach Kunden fragen.",
  probedNote:
    "Jemand versucht immer wieder, die Anweisungen des Assistenten zu ändern. Die Kontakte werden nach drei Versuchen für einen Tag gestoppt; sehen Sie sich die Gespräche an.",
  empty: "Keine geprüften Antworten in den letzten 7 Tagen.",
  issueLabel: "Anstieg beim Antwortschutz",
};
