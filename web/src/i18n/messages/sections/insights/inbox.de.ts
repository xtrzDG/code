/** `inbox.*` in German: the team inbox (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { inboxEn } from "./inbox.en";

export const inboxDe: Translation<typeof inboxEn> = {
  title: "Posteingang",
  viewsLabel: "Gespräche anzeigen",
  views: {
    needs_person: "Braucht eine Person",
    requests: "Anfragen",
    mine: "Meine",
    unassigned: "Nicht zugewiesen",
    all: "Alle",
  },
  moreViews: "Mehr",
  moreViewsChosen: "Mehr: {view}",
  viewCount: {
    one: "{count} Gespräch",
    other: "{count} Gespräche",
  },
  empty: {
    needs_person: {
      title: "Niemand wartet auf eine Person",
      description: "Wenn der Assistent ein Gespräch an Ihr Team übergibt, erscheint es hier sofort.",
    },
    requests: {
      title: "Keine offenen Anfragen",
      description: "Bankette, Gruppenbesuche und andere Anfragen, die der Assistent aufnimmt, warten hier, bis sich jemand darum kümmert.",
    },
    mine: {
      title: "Ihnen ist nichts zugewiesen",
      description: "Gespräche, die Sie übernehmen oder die Ihnen gegeben werden, warten hier, solange sie das Team brauchen.",
    },
    unassigned: {
      title: "Alles hat jemanden",
      description: "Gespräche, die das Team brauchen und um die sich niemand kümmert, erscheinen hier.",
    },
    all: {
      title: "Noch keine Gespräche",
      description: "Gespräche erscheinen hier, sobald Kunden dem Assistenten schreiben oder ihn anrufen.",
    },
  },
  showAll: "Alle Gespräche ansehen",
  loading: "Der Posteingang wird geladen…",
  listLabel: "Gespräche",
  searchLabel: "Alle Gespräche durchsuchen",
  searchPlaceholder: "Suchen: Name, Telefon oder Text",
  filters: {
    open: "Filter",
    openWithCount: "Filter ({count})",
    title: "Filter",
    description: "Zeitraum, Status und Testgespräche gelten für alle Gespräche und für die Suche.",
    show: "Gespräche anzeigen",
    clear: "Filter zurücksetzen",
  },
  clearSearch: "Suche löschen",
  row: {
    unassigned: "Niemand zugewiesen",
    you: "Sie",
    notes: {
      one: "{count} Notiz",
      other: "{count} Notizen",
    },
    request: "Anfrage: {type}",
  },
  assign: {
    open: "Zuweisen",
    menuLabel: "Wer dieses Gespräch bearbeitet",
    handledBy: "Bearbeitet von {name}",
    handledByYou: "Sie bearbeiten es",
    automatically: "Automatisch zugewiesen",
    nobody: "Noch bearbeitet es niemand",
    takeIt: "Übernehmen",
    unassign: "Zuweisung aufheben",
    you: "Sie",
    teammate: "Teammitglied",
    waiting: {
      one: "{count} wartet",
      other: "{count} warten",
    },
    loading: "Das Team wird geladen…",
    assigned: "{name} bearbeitet dieses Gespräch jetzt",
    taken: "Sie bearbeiten dieses Gespräch jetzt",
    cleared: "Jetzt ist niemand zugewiesen",
    conflict: "Jemand anderes hat gerade geändert, wer dieses Gespräch bearbeitet. So ist der aktuelle Stand.",
    colleague: "Eine Kollegin oder ein Kollege bearbeitet dieses Gespräch. Bitten Sie einen Inhaber, es zu übergeben.",
    notMember: "Diese Person ist nicht mehr im Team.",
  },
};
