/** `leads.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { leadsEn } from "./leads.en";

export const leadsIt: Translation<typeof leadsEn> = {
  loading: "Caricamento dei lead…",
  status: {
    new: "Nuovo",
    in_progress: "In corso",
    won: "Vinto",
    lost: "Perso",
  },
  type: {
    banquet: "Banchetto",
    group: "Gruppo",
    corporate: "Evento aziendale",
    order: "Ordine",
    viewing: "Visita",
    otherRequest: "Altra richiesta",
  },
  updated: "Lead spostato in “{status}”",
};
