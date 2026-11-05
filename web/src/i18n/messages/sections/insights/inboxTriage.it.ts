/** `inboxTriage.*` in Italian: density, keys and bulk actions in the inbox (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { inboxTriageEn } from "./inboxTriage.en";

export const inboxTriageIt: Translation<typeof inboxTriageEn> = {
  density: {
    label: "Righe",
    comfortable: "Ampie",
    compact: "Compatte",
  },
  resize: {
    label: "Larghezza dell'elenco delle conversazioni",
    hint: "Trascina o usa i tasti freccia. Con un doppio clic torna alla larghezza standard.",
  },
  keys: {
    open: "Scorciatoie da tastiera",
    title: "Scorciatoie da tastiera",
    description: "Scorri l'elenco senza mouse. I tasti funzionano quando non stai scrivendo.",
    listHint: "J e K scorrono l'elenco, E segna come risolta, A prende in carico la conversazione, X la seleziona, il punto interrogativo mostra tutti i tasti.",
    resolveNote: "Risolta: un passaggio a una persona torna all'assistente e una richiesta aperta viene segnata come vinta. Puoi annullare dal messaggio che compare subito dopo.",
    actions: {
      next: "Conversazione successiva",
      previous: "Conversazione precedente",
      open: "Apri la conversazione",
      resolve: "Segna come risolta",
      assign: "Prendila in carico: la gestisci tu",
      select: "Selezionala per un'azione di gruppo",
      search: "Cerca",
      help: "Mostra questi tasti",
      clear: "Annulla la selezione",
    },
  },
  select: {
    row: "Seleziona la conversazione con {name}",
    all: "Seleziona tutte le conversazioni con qualcosa da risolvere",
    count: {
      one: "{count} selezionata",
      other: "{count} selezionate",
    },
    resolve: "Segna come risolte",
    clear: "Annulla la selezione",
  },
  resolved: {
    one: "{count} conversazione risolta",
    other: "{count} conversazioni risolte",
  },
  resolvedPartly: "{done} su {total} risolte. Qualcuno ha modificato le altre poco prima; l'elenco mostra la loro situazione attuale.",
  undone: "Ripristinato com'era",
  undonePartly: "Alcune non è stato possibile ripristinarle: nel frattempo qualcuno le ha modificate. L'elenco mostra la loro situazione attuale.",
  nothingToResolve: "In questa conversazione non c'è nulla in sospeso: nessun passaggio a una persona né richiesta aperta.",
  alreadyYours: "Gestisci già tu questa conversazione.",
  age: {
    now: "ora",
    minutes: "{count} min",
    hours: "{count} h",
    days: "{count} g",
  },
  details: {
    source: "Provenienza",
    assignee: "Gestita da",
    lastMessage: "Ultimo messaggio",
  },
};
