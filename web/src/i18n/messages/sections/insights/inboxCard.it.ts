/** `inboxCard.*` in Italian: the conversation card in the inbox (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { inboxCardEn } from "./inboxCard.en";

export const inboxCardIt: Translation<typeof inboxCardEn> = {
  back: "Torna alle conversazioni",
  openDetails: "Dettagli",
  openDetailsOf: "Dettagli della conversazione con {name}",
  openNotes: "Note",
  openNotesCount: {
    one: "Note ({count})",
    other: "Note ({count})",
  },
  panelLabel: "Informazioni sulla conversazione",
  panelTabs: "Pannello",
  messageContext: {
    story_reply: "Risposta alla tua storia",
    story_mention: "Menzione nella storia del cliente",
  },
  offeredChoices: "Opzioni proposte",
  actions: {
    label: "Azioni rapide",
    resolve: "Risolvi",
    resolveHint: "L'assistente torna a rispondere a questo cliente",
    call: "Chiama",
    callLabel: "Chiama {phone}",
    book: "Prenota",
  },
  work: {
    needsPerson: "Serve una persona",
    request: "Richiesta",
    requestStatus: "Stato della richiesta",
    since: "aperta {time}",
  },
  details: {
    customer: "Cliente",
    channel: "Canale",
    language: "Lingua",
    started: "Iniziata",
    lastMessage: "Ultimo messaggio",
  },
  technical: {
    title: "Dettagli tecnici",
    hint: "Cosa c'è dietro le risposte: l'aggiornamento dell'assistente che le ha date e le sue richieste esatte ai tuoi dati.",
    tokens: "Token",
    cost: "Costo AI",
    version: "Aggiornamento dell'assistente",
    message: "Dettagli tecnici di questo messaggio",
  },
  notes: {
    title: "Note",
    hint: "Le vede solo il tuo team",
    description: "Le note restano all'interno del tuo team: il cliente e l'assistente non le vedono mai.",
    placeholder: "Cosa è stato promesso, chi richiama, cosa ricordare…",
    add: "Aggiungi nota",
    adding: "Salvataggio…",
    added: "Nota salvata. La vede solo il tuo team.",
    unknownAuthor: "Ex membro del team",
    delete: "Elimina nota",
    confirmDelete: {
      title: "Eliminare questa nota?",
      description: "Sparirà per tutto il team.",
      confirm: "Elimina",
    },
    deleted: "Nota eliminata",
    empty: "Ancora nessuna nota. Una nota aiuta chi viene dopo: cosa è stato promesso, chi richiama.",
    loading: "Caricamento delle note…",
    length: "{count} / {max}",
  },
  quickReplies: {
    open: "Risposte rapide",
    hint: "Digita / per le risposte rapide",
    listLabel: "Risposte rapide",
    loading: "Caricamento delle risposte rapide…",
    empty: "Ancora nessuna risposta rapida.",
    emptyOwner: "Crea le risposte che invii spesso in Impostazioni → Risposte rapide.",
    manage: "Gestisci le risposte rapide",
    noMatch: "Nessuna risposta rapida corrisponde a “/{query}”.",
    missing: "Da compilare prima dell'invio:",
    fillFieldLabel: "Valore per {variable}",
    fill: "Compila",
    placeholdersLeft: "Prima dell'invio compila le parti tra parentesi graffe: {variables}.",
    variables: {
      name: "nome del cliente",
      booking_time: "orario della prenotazione",
      business_name: "nome dell'attività",
    },
  },
  composer: {
    placeholder: "Scrivi al cliente…",
    sendLabel: "Invia",
  },
  request: {
    updated: "Richiesta: {status}",
  },
  resolveConfirm: {
    title: "Segnare come risolta?",
    description: "{name}: l'assistente torna a rispondere a questo cliente.",
    confirm: "Risolvi",
  },
  resolved: "Segnata come risolta. L'assistente torna a rispondere a questo cliente.",
  reopened: "Il passaggio a una persona è di nuovo aperto. L'assistente resta in silenzio finché non viene risolto.",
};
