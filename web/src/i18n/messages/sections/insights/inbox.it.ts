/** `inbox.*` in Italian: the team inbox (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { inboxEn } from "./inbox.en";

export const inboxIt: Translation<typeof inboxEn> = {
  title: "Conversazioni",
  viewsLabel: "Mostra conversazioni",
  views: {
    needs_person: "Serve una persona",
    requests: "Richieste",
    mine: "Mie",
    unassigned: "Non assegnate",
    all: "Tutte",
  },
  moreViews: "Altro",
  moreViewsChosen: "Altro: {view}",
  viewCount: {
    one: "{count} conversazione",
    other: "{count} conversazioni",
  },
  empty: {
    needs_person: {
      title: "Nessuno attende una persona",
      description: "Quando l'assistente passa una conversazione al tuo team, la trovi subito qui.",
    },
    requests: {
      title: "Nessuna richiesta aperta",
      description: "Banchetti, visite di gruppo e altre richieste raccolte dall'assistente restano qui finché qualcuno non se ne occupa.",
    },
    mine: {
      title: "Niente di assegnato a te",
      description: "Le conversazioni che prendi in carico, o che ti vengono assegnate, restano qui finché richiedono il team.",
    },
    unassigned: {
      title: "Ogni conversazione ha un responsabile",
      description: "Qui compaiono le conversazioni che richiedono il team ma che nessuno sta gestendo.",
    },
    all: {
      title: "Ancora nessuna conversazione",
      description: "Le conversazioni compaiono qui non appena i clienti scrivono o chiamano l'assistente.",
    },
  },
  showAll: "Vedi tutte le conversazioni",
  loading: "Caricamento delle conversazioni…",
  listLabel: "Conversazioni",
  searchLabel: "Cerca in tutte le conversazioni",
  searchPlaceholder: "Cerca: nome, telefono o testo",
  filters: {
    open: "Filtri",
    openWithCount: "Filtri ({count})",
    title: "Filtri",
    description: "Periodo, stato e conversazioni di prova valgono per tutte le conversazioni e per la ricerca.",
    show: "Mostra conversazioni",
    clear: "Azzera i filtri",
  },
  clearSearch: "Cancella la ricerca",
  row: {
    unassigned: "Non assegnata",
    you: "Tu",
    notes: {
      one: "{count} nota",
      other: "{count} note",
    },
    request: "Richiesta: {type}",
  },
  assign: {
    open: "Assegna",
    menuLabel: "Chi gestisce questa conversazione",
    handledBy: "Gestita da {name}",
    handledByYou: "La gestisci tu",
    automatically: "Assegnata automaticamente",
    nobody: "Nessuno la gestisce ancora",
    takeIt: "Prendila in carico",
    unassign: "Rimuovi assegnazione",
    you: "Tu",
    teammate: "Membro del team",
    waiting: {
      one: "{count} in attesa",
      other: "{count} in attesa",
    },
    loading: "Caricamento del team…",
    assigned: "Ora {name} gestisce questa conversazione",
    taken: "Ora gestisci tu questa conversazione",
    cleared: "Ora non è assegnata a nessuno",
    conflict: "Qualcun altro ha appena cambiato chi gestisce questa conversazione. Ecco la situazione attuale.",
    colleague: "Questa conversazione è gestita da un collega. Chiedi a un titolare di passartela.",
    notMember: "Quella persona non fa più parte del team.",
  },
};
