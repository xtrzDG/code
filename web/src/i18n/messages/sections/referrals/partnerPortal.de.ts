/** `partnerPortal.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { partnerPortalEn } from "./partnerPortal.en";

export const partnerPortalDe: Translation<typeof partnerPortalEn> = {
  title: "Partnerportal",
  description: "Ihre Links, die Unternehmen, die sie gebracht haben, und was Sie verdient haben.",
  rate: "Ihre Provision: {rate} jeder Rechnung, die diese Unternehmen bezahlen, vor Steuern.",
  paused: "Ihre Partnerschaft ist pausiert: Neue Zahlungen bringen keine Provision, bis das Plattform-Team sie fortsetzt.",
  legal: "Ihr Vertrag und wie Auszahlungen Sie erreichen, werden mit dem Plattform-Team vereinbart.",
  links: {
    title: "Ihre Links",
    description: "Erstellen Sie für jeden Ort, an dem Sie ihn teilen, einen Link: Das Tag zeigt, woher die Anmeldungen kamen.",
    none: "Sie haben noch keine Codes: Das Plattform-Team fügt sie hinzu.",
    source: "Wo Sie ihn teilen",
    sourcePlaceholder: "Instagram",
    sourceHint: "Optional. Lateinische Buchstaben, Ziffern, Punkte, Bindestriche und Unterstriche.",
    sourceInvalid: "Verwenden Sie nur lateinische Buchstaben, Ziffern, Punkte, Bindestriche und Unterstriche.",
    code: "Code",
    qrLabel: "QR-Code des Links mit {code}",
    showQr: "QR-Code",
    hideQr: "QR-Code ausblenden",
  },
  totals: {
    title: "Provisionen",
    businesses: "Gebrachte Unternehmen",
    paying: "Bereits bezahlt",
    accrued: "Offen",
    paid: "Ausgezahlt",
    invoices: "{count} Rechnungen",
    none: "Noch keine Provisionen.",
  },
  businesses: {
    title: "Unternehmen, die Sie gebracht haben",
    empty: "Noch keine Unternehmen. Teilen Sie Ihren Link, um das erste zu bringen.",
    business: "Unternehmen",
    country: "Land",
    plan: "Tarif",
    status: "Status",
    signedUp: "Angemeldet",
    firstPaid: "Erste Zahlung",
    notYet: "Noch nicht",
    unnamed: "Unternehmen",
  },
  commissions: {
    title: "Provision je Rechnung",
    empty: "Noch keine Provisionen: Sie erscheinen, wenn ein von Ihnen gebrachtes Unternehmen bezahlt.",
    month: "Monat",
    business: "Unternehmen",
    base: "Rechnung vor Steuern",
    amount: "Provision",
    status: "Status",
    statuses: {
      accrued: "Offen",
      paid: "Ausgezahlt",
    },
  },
  showMore: "Mehr anzeigen",
  loading: "Wird geladen…",
};
