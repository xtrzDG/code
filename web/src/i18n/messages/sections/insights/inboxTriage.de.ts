/** `inboxTriage.*` in German: density, keys and bulk actions in the inbox (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { inboxTriageEn } from "./inboxTriage.en";

export const inboxTriageDe: Translation<typeof inboxTriageEn> = {
  density: {
    label: "Zeilen",
    comfortable: "Großzügig",
    compact: "Kompakt",
  },
  resize: {
    label: "Breite der Gesprächsliste",
    hint: "Ziehen oder die Pfeiltasten verwenden. Ein Doppelklick stellt die übliche Breite wieder her.",
  },
  keys: {
    open: "Tastenkürzel",
    title: "Tastenkürzel",
    description: "Arbeiten Sie die Liste ohne Maus ab. Die Tasten funktionieren, solange Sie nicht tippen.",
    listHint: "J und K bewegen durch die Liste, E erledigt, A übernimmt das Gespräch, X wählt es aus, das Fragezeichen zeigt alle Tasten.",
    resolveNote: "Erledigt: Eine Übergabe geht an den Assistenten zurück, und eine offene Anfrage wird als gewonnen markiert. Rückgängig steht in der folgenden Meldung.",
    actions: {
      next: "Nächstes Gespräch",
      previous: "Vorheriges Gespräch",
      open: "Gespräch öffnen",
      resolve: "Erledigen",
      assign: "Übernehmen: Sie bearbeiten es",
      select: "Für eine Sammelaktion auswählen",
      search: "Suchen",
      help: "Diese Tasten anzeigen",
      clear: "Auswahl aufheben",
    },
  },
  select: {
    row: "Gespräch mit {name} auswählen",
    all: "Alle Gespräche mit etwas zu erledigen auswählen",
    count: {
      one: "{count} ausgewählt",
      other: "{count} ausgewählt",
    },
    resolve: "Erledigen",
    clear: "Auswahl aufheben",
  },
  resolved: {
    one: "{count} Gespräch erledigt",
    other: "{count} Gespräche erledigt",
  },
  resolvedPartly: "{done} von {total} erledigt. Jemand hat die anderen kurz vorher geändert; die Liste zeigt ihren aktuellen Stand.",
  undone: "Wieder wie vorher",
  undonePartly: "Einige konnten nicht zurück: Jemand hat sie inzwischen geändert. Die Liste zeigt ihren aktuellen Stand.",
  nothingToResolve: "In diesem Gespräch wartet nichts: keine offene Übergabe oder Anfrage.",
  alreadyYours: "Sie bearbeiten dieses Gespräch bereits.",
  age: {
    now: "jetzt",
    minutes: "{count} Min.",
    hours: "{count} Std.",
    days: "{count} T.",
  },
  details: {
    label: "Über dieses Gespräch",
    source: "Kam von",
    assignee: "Bearbeitet von",
    lastMessage: "Letzte Nachricht",
  },
};
