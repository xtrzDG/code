/** `growthValue.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { growthValueEn } from "./growthValue.en";

export const growthValueDe: Translation<typeof growthValueEn> = {
  label: "Vom Assistenten zurückgewonnene Buchungen",
  waitlist: { one: "{count} von der Warteliste", other: "{count} von der Warteliste" },
  campaign: { one: "{count} nach einer Wiederkehr-Nachricht", other: "{count} nach Wiederkehr-Nachrichten" },
  worth: "≈ {money}",
  waitlistHint: "Frei gewordene Plätze, die wartende Kunden übernommen haben.",
  campaignHint: "Kunden, die nach der Nachricht erneut gebucht haben.",
  rows: {
    waitlistBookings: "Buchungen von der Warteliste",
    waitlistValue: "Wert der Buchungen von der Warteliste",
    campaignBookings: "Buchungen nach Wiederkehr-Nachrichten",
    campaignValue: "Wert der Buchungen nach Wiederkehr-Nachrichten",
  },
};
