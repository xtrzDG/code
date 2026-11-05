/** `adminSystem.folds.*` texts of the System page's folded rows on a phone, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminSystemFoldsEn } from "./adminSystemFolds.en";

export const adminSystemFoldsIt: Translation<typeof adminSystemFoldsEn> = {
  none: "Nessuno",
  live: { one: "{count} attivo", other: "{count} attivi" },
  stale: { one: "{count} inattivo", other: "{count} inattivi" },
  allClosed: "Tutti chiusi",
  notClosed: { one: "{count} non chiuso", other: "{count} non chiusi" },
  due: { one: "{count} da eseguire", other: "{count} da eseguire" },
  deadJobs: { one: "{count} job", other: "{count} job" },
  noneInError: "Nessuno in errore",
  inError: { one: "{count} in errore", other: "{count} in errore" },
  expiring: { one: "{count} token in scadenza", other: "{count} token in scadenza" },
  allMatch: "Tutto corrisponde",
  noneOpen: "Nessuno aperto",
  open: { one: "{count} aperto", other: "{count} aperti" },
};
