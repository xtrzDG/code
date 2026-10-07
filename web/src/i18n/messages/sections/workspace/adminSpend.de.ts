/** `adminSpend.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminSpendEn } from "./adminSpend.en";

export const adminSpendDe: Translation<typeof adminSpendEn> = {
  title: "Ausgaben heute",
  description: "Was die Plattform ihren Anbietern für {day} (UTC) schuldet. Kosten, die ein Anbieter noch nicht gemeldet hat, werden zu Planpreisen gezählt.",
  total: "Gesamt heute",
  weekMean: "Tagesmittel der 7 Tage davor: {amount}",
  spike: "Weit über dem Üblichen",
  budget: "{percent} % des Tagesbudgets von {amount}",
  budgetLabel: "Verbrauchtes Tagesbudget",
  noBudget: "Kein Tagesbudget festgelegt (PLATFORM_DAILY_SPEND_BUDGET_USD).",
  providersLabel: "Ausgaben nach Anbieter",
  providers: {
    language_model: "KI-Modell",
    voice: "Sprachagent",
    telephony: "Anrufe",
    whatsapp: "WhatsApp-Vorlagen",
    transcription: "Transkription von Sprachnachrichten",
  },
  brakedTitle: "Kunden über einem Ausgabenlimit",
  brakedNone: "Heute hat kein Kunde ein Ausgabenlimit überschritten.",
  levels: {
    soft_limit: "Günstigeres Modell",
    hard_limit: "Nur Anfragen",
  },
  brakedLine: "{spend} von {limit}, seit {time}",
};
