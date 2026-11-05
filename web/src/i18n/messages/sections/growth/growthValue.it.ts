/** `growthValue.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { growthValueEn } from "./growthValue.en";

export const growthValueIt: Translation<typeof growthValueEn> = {
  label: "Prenotazioni recuperate dall’assistente",
  waitlist: { one: "{count} dalla lista d’attesa", other: "{count} dalla lista d’attesa" },
  campaign: { one: "{count} dopo un messaggio di richiamo", other: "{count} dopo i messaggi di richiamo" },
  worth: "≈ {money}",
  waitlistHint: "Posti liberati presi da clienti in attesa.",
  campaignHint: "Clienti che hanno prenotato di nuovo dopo il messaggio.",
  rows: {
    waitlistBookings: "Prenotazioni dalla lista d’attesa",
    waitlistValue: "Valore delle prenotazioni dalla lista d’attesa",
    campaignBookings: "Prenotazioni dopo i messaggi di richiamo",
    campaignValue: "Valore delle prenotazioni dopo i messaggi di richiamo",
  },
};
