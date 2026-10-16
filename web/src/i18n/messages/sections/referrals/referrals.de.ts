/** `referrals.*` in German: inviting a business (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { referralsEn } from "./referrals.en";

export const referralsDe: Translation<typeof referralsEn> = {
  title: "Unternehmen einladen — ein Monat gratis",
  lead: "Teilen Sie Ihren Link mit einem Unternehmen, das Sie kennen. Wenn es seine erste Rechnung bezahlt, bekommen Sie beide einen Monat Ihres Tarifs gratis.",
  terms: "Der Monat wird Ihren nächsten Rechnungen gutgeschrieben. Ihre eigenen weiteren Unternehmen zählen nicht.",
  menu: "Unternehmen einladen",
  menuHint: "Ein Monat gratis für Sie beide",
  linkLabel: "Ihr Einladungslink",
  copy: "Link kopieren",
  share: "Teilen",
  shareText: "Wir antworten unseren Kunden mit {app}. Melden Sie sich über meinen Link an, dann bekommen wir beide einen Monat gratis:",
  showQr: "QR-Code anzeigen",
  hideQr: "QR-Code ausblenden",
  qrLabel: "QR-Code Ihres Einladungslinks",
  noLink: "Ihr Einladungslink ist noch nicht fertig. Versuchen Sie es später erneut.",
  loading: "Ihre Einladung wird geladen…",
  statsLabel: "Ihre Einladungen",
  invited: "Angemeldet",
  paid: "Bezahlt",
  rewarded: "Verdiente Monate",
  close: "Schließen",
  poweredBy: {
    title: "„Powered by“-Link",
    description: "Ein kleiner Link mit Ihrem Einladungscode unter dem Chat, auf der Chat-Seite und auf der gedruckten Karte.",
    toggle: "„Powered by“-Link anzeigen",
    plusOnly: "Ihn zu entfernen ist Teil des Plus-Tarifs.",
    hidden: "Aus: Chat, Seite und Karte zeigen keinen Link.",
    saved: "Gespeichert",
    footer: "Powered by {app}",
  },
  partnerPortal: "Partnerportal",
};
