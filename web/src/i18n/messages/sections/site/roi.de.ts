/** `roi.*` in German: the missed-requests calculator (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { roiEn } from "./roi.en";

export const roiDe: Translation<typeof roiEn> = {
  title: "Was kosten Sie die Anfragen, die Sie verpassen?",
  subtitle: "Zählen Sie nur, was ankommt, wenn niemand antworten kann. Der Rest ist einfache Rechnung, mit Ihren Zahlen.",
  niche: "Ihre Branche",
  missed: "Anrufe und Nachrichten, die Sie pro Monat verpassen oder zu spät beantworten",
  missedHint: "Ein Anruf, den niemand angenommen hat, eine Nachricht, die erst Stunden später beantwortet wurde",
  afterHours: "Davon außerhalb der Arbeitszeit",
  check: "Durchschnittlicher Bon",
  checkHint: "Ein typischer Bon für diese Branche; ändern Sie ihn auf Ihren",
  checkUnknown: "Die Beträge schwanken hier stark: Geben Sie Ihren ein",
  conversion: "Anfragen, die zur Buchung werden",
  plan: "Mit dem Tarif vergleichen",
  percent: "{value} %",
  resultLabel: "Der Assistent würde etwa bringen",
  bookings: {
    one: "{count} Buchung mehr pro Monat",
    other: "{count} Buchungen mehr pro Monat",
  },
  bookingsUnderOne: "weniger als eine Buchung mehr pro Monat",
  perMonth: "{value} pro Monat",
  multiple: "das {multiple}-Fache des Preises von {plan} ({price} pro Monat)",
  belowPrice: "Weniger als der Preis von {plan} ({price} pro Monat): Rechnen Sie auch die Zeit mit, die Ihr Team bei Antworten spart.",
  breakEven: {
    one: "{count} Buchung pro Monat bezahlt den Tarif",
    other: "{count} Buchungen pro Monat bezahlen den Tarif",
  },
  noCheck: "Geben Sie einen durchschnittlichen Bon ein, um den Betrag zu sehen.",
  breakdown: {
    label: "So setzt es sich zusammen",
    answered: "Antworten außerhalb der Arbeitszeit",
    bookings: "Buchungen darunter",
    check: "Durchschnittlicher Bon",
  },
  note: "Eine Schätzung aus Ihren Zahlen, kein Versprechen. Im Dashboard sehen Sie die echten Werte: beantwortete Anfragen, Buchungen und was sie gebracht haben.",
  currency: "in {currency}",
};
