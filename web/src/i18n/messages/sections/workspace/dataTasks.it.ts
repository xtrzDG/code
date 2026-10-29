/** `dataTasks.*` texts of the admin's post-deploy data tasks card, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { dataTasksEn } from "./dataTasks.en";

export const dataTasksIt: Translation<typeof dataTasksEn> = {
  title: "Attività sui dati dopo un deploy",
  description: {
    one: "Migrazioni dei documenti e riempimenti delle colonne di lookup che il worker batch esegue da solo, a blocchi di {size} riga. La release successiva viene promossa solo quando ogni attività è completata.",
    other: "Migrazioni dei documenti e riempimenti delle colonne di lookup che il worker batch esegue da solo, a blocchi di {size} righe. La release successiva viene promossa solo quando ogni attività è completata.",
  },
  open: {
    one: "{count} attività aperta",
    other: "{count} attività aperte",
  },
  allDone: "Tutte le attività sono completate",
  failed: "Non riuscite: {count}",
  stalled: "Bloccate da oltre un giorno: {count}",
  settled: "Nessun worker di un'altra release è in esecuzione: le attività vengono eseguite ora.",
  waiting: "In attesa che si fermino i worker di {releases} (circa {time}).",
  waitingUnnamed: "In attesa che si fermino i worker di una release senza nome (circa {time}).",
  none: "Questa release non ha attività sui dati.",
  openCaption: "Attività sui dati aperte",
  doneCaption: "Attività sui dati completate",
  showDone: {
    one: "Mostra {count} attività completata",
    other: "Mostra {count} attività completate",
  },
  hideDone: "Nascondi le attività completate",
  columns: {
    task: "Attività",
    status: "Stato",
    progress: "Avanzamento",
    when: "Quando",
    actions: "Azioni",
  },
  kinds: {
    migrate_documents: "Riscrivi i documenti alla versione {version}",
    backfill_lookup: "Riempi la colonna di lookup",
  },
  statuses: {
    pending: "In attesa",
    running: "In esecuzione",
    done: "Completata",
    failed: "Non riuscita",
  },
  lists: {
    customers: "Elenco clienti",
    knowledge: "Elenco conoscenze",
  },
  holdsBack: "Blocca: {lists}",
  rows: { one: "{scanned} su circa {estimate} riga", other: "{scanned} su circa {estimate} righe" },
  rowsUnknown: { one: "{scanned} riga esaminata", other: "{scanned} righe esaminate" },
  changed: { one: "Modifiche: {count}, {batches} blocco", other: "Modifiche: {count}, {batches} blocchi" },
  failedRows: { one: "{count} riga non è stata aggiornata: {keys}", other: "{count} righe non sono state aggiornate: {keys}" },
  dueSince: "In attesa dal {time}",
  doneAt: "Completata il {time}",
  lastBatch: "Ultimo blocco il {time}",
  isStalled: "Bloccata",
  retry: "Riesegui",
  retried: "L'attività ripercorre di nuovo la sua tabella.",
  indexing: {
    title: "Indicizzazione in corso",
    body: "Un aggiornamento dei dati successivo all'ultima release è ancora in corso, quindi per qualche minuto alcune voci meno recenti potrebbero mancare da questo elenco.",
  },
};
