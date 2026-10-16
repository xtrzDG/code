/** `leads.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { leadsEn } from "./leads.en";

export const leadsDe: Translation<typeof leadsEn> = {
  loading: "Anfragen werden geladen…",
  status: {
    new: "Neu",
    in_progress: "In Bearbeitung",
    won: "Gewonnen",
    lost: "Verloren",
  },
  type: {
    banquet: "Bankett",
    group: "Gruppe",
    corporate: "Firmenveranstaltung",
    order: "Bestellung",
    viewing: "Besichtigung",
    otherRequest: "Andere Anfrage",
  },
  updated: "Anfrage auf „{status}“ gesetzt",
};
