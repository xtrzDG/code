/** `leads.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { leadsEn } from "./leads.en";

export const leadsDe: Translation<typeof leadsEn> = {
  loading: "Anfragen werden geladen…",
  tabsLabel: "Status der Anfrage",
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
  statusOf: "Status der Anfrage von {name}",
  statusLabel: "Status",
  requestedDate: "Datum",
  partySize: "Personen",
  budget: "Budget",
  source: "Quelle",
  received: "Eingegangen",
  details: "Details",
  showDetails: "Details",
  contact: "Kunde",
  updated: "Anfrage auf „{status}“ gesetzt",
  emptyTitle: "Noch keine Anfragen",
  emptyDescription:
    "Wenn ein Kunde etwas möchte, das der Assistent nicht selbst bucht (ein Bankett, eine Gruppe, eine Bestellung), kommt die Anfrage hierher für die Führungskraft.",
};
