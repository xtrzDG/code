/** `dataTasks.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { dataTasksEn } from "./dataTasks.en";

export const dataTasksDe: Translation<typeof dataTasksEn> = {
  title: "Datenaufgaben nach einem Deploy",
  description:
    "Dokumentmigrationen und das Auffüllen von Suchspalten, die der Batch-Worker selbst in Stapeln von {size} Zeilen ausführt. Das nächste Release wird erst befördert, wenn jede Aufgabe erledigt ist.",
  open: {
    one: "{count} Aufgabe offen",
    other: "{count} Aufgaben offen",
  },
  allDone: "Jede Aufgabe ist erledigt",
  failed: "{count} fehlgeschlagen",
  stalled: "{count} seit über einem Tag festgefahren",
  settled: "Kein Worker eines anderen Releases läuft: Die Aufgaben laufen jetzt.",
  waiting: "Warten, bis die Worker von {releases} stoppen (etwa {time}).",
  waitingUnnamed: "Warten, bis die Worker eines unbenannten Releases stoppen (etwa {time}).",
  none: "Dieses Release hat keine Datenaufgaben.",
  openCaption: "Offene Datenaufgaben",
  doneCaption: "Erledigte Datenaufgaben",
  showDone: {
    one: "{count} erledigte Aufgabe anzeigen",
    other: "{count} erledigte Aufgaben anzeigen",
  },
  hideDone: "Erledigte Aufgaben ausblenden",
  columns: {
    task: "Aufgabe",
    status: "Status",
    progress: "Fortschritt",
    when: "Wann",
    actions: "Aktionen",
  },
  kinds: {
    migrate_documents: "Dokumente auf Version {version} umschreiben",
    backfill_lookup: "Suchspalte auffüllen",
  },
  statuses: {
    pending: "Wartet",
    running: "Läuft",
    done: "Erledigt",
    failed: "Fehlgeschlagen",
  },
  lists: {
    customers: "Kundenliste",
    knowledge: "Wissensliste",
  },
  holdsBack: "Hält zurück: {lists}",
  rows: "{scanned} von etwa {estimate} Zeilen",
  rowsUnknown: "{scanned} Zeilen angesehen",
  changed: "{count} geändert, {batches} Stapel",
  failedRows: "{count} Zeilen konnten nicht aktualisiert werden: {keys}",
  dueSince: "Fällig seit {time}",
  doneAt: "Erledigt {time}",
  lastBatch: "Letzter Stapel {time}",
  isStalled: "Festgefahren",
  retry: "Erneut durchgehen",
  retried: "Die Aufgabe geht ihre Tabelle erneut durch.",
  indexing: {
    title: "Indexierung läuft noch",
    body: "Eine Datenaktualisierung nach dem letzten Release läuft noch, daher können einige ältere Einträge für ein paar Minuten in dieser Liste fehlen.",
  },
};
