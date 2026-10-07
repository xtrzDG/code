/** `adminChurn.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminChurnEn } from "./adminChurn.en";

export const adminChurnDe: Translation<typeof adminChurnEn> = {
  title: "Warum Inhaber kündigen",
  description:
    "Kündigungen im Zeitraum nach dem vom Inhaber gewählten Grund, die stattdessen angenommenen Angebote, saisonale Pausen und die Nachrichten 14 und 30 Tage nach einer Kündigung.",
  empty: "Keine Kündigungen, Angebote oder Pausen in diesem Zeitraum.",
  stats: {
    cancellations: "Gekündigt",
    saved: "Mit einem Angebot geblieben",
    pausesScheduled: "Geplante Pausen",
    pausesEnded: "Beendete Pausen",
    winBackSent: "Rückgewinnungsnachrichten",
    returned: "Danach zurückgekommen",
  },
  reason: "Grund",
  cancelled: "Gekündigt",
  tookOffer: "Stattdessen das Angebot angenommen",
  noReason: "Nicht gefragt (vor der Frage)",
  offersTitle: "Angenommene Angebote",
  commentsTitle: "In den Worten der Inhaber",
  openClient: "Kunden öffnen",
};
