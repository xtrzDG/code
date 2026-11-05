/** `adminChurn.*` texts of the platform admin's Metrics page, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminChurnEn } from "./adminChurn.en";

export const adminChurnIt: Translation<typeof adminChurnEn> = {
  title: "Perché i titolari disdicono",
  description:
    "Disdette del periodo per motivo scelto dal titolare, offerte accettate al loro posto, pause stagionali e messaggi inviati 14 e 30 giorni dopo una disdetta.",
  empty: "Nessuna disdetta, offerta o pausa in questo periodo.",
  stats: {
    cancellations: "Disdette",
    saved: "Rimasti con un'offerta",
    pausesScheduled: "Pause programmate",
    pausesEnded: "Pause terminate",
    winBackSent: "Messaggi di riconquista",
    returned: "Tornati dopo il messaggio",
  },
  reason: "Motivo",
  cancelled: "Disdette",
  tookOffer: "Hanno accettato l'offerta",
  noReason: "Non chiesto (prima della domanda)",
  offersTitle: "Offerte accettate",
  commentsTitle: "Con le parole dei titolari",
  openClient: "Apri il cliente",
};
