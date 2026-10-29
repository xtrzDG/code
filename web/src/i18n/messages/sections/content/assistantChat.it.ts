/** `assistantChat.*` in Italian: the test chat (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { assistantChatEn } from "./assistantChat.en";

export const assistantChatIt: Translation<typeof assistantChatEn> = {
  chat: {
    newConversation: "Nuova conversazione",
    logLabel: "Conversazione di prova",
    emptyTitle: "Avvia una conversazione di prova",
    emptyDescription: "Chiedi quello che chiedono i tuoi clienti, in qualsiasi lingua. Oppure prova una di queste:",
    suggestions: {
      hours: "Quali sono i vostri orari di apertura?",
      price: "Quanto costa?",
      booking: "Vorrei prenotare per domani alle 19 per 4 persone",
      human: "Posso parlare con una persona?",
    },
    typing: "L'assistente sta scrivendo…",
    choicesLabel: "Risposte da toccare",
    inputLabel: "Messaggio",
    placeholder: "Scrivi un messaggio…",
    inputHint: {
      one: "Invio per inviare, Maiusc+Invio per andare a capo. Massimo {count} carattere.",
      other: "Invio per inviare, Maiusc+Invio per andare a capo. Massimo {count} caratteri.",
    },
    send: "Invia",
    failed: "Non inviato.",
    silent: "L'assistente non risponde: la conversazione è passata a una persona.",
    handedOffTitle: "Passata a una persona",
    handedOffDescription: "In una chat reale ora risponderebbe il tuo personale, quindi l'assistente non interviene. Avvia una nuova conversazione per continuare a provare.",
    guardRewritten: "Numeri verificati e corretti",
    guardHandedOff: "Passata a una persona: dubbio su un numero",
    handedOff: "Passata a una persona",
    bookingsCreated: { one: "Prenotazione di prova creata", other: "{count} prenotazioni di prova create" },
    leadsCreated: { one: "Richiesta di prova creata", other: "{count} richieste di prova create" },
    toolCalls: { one: "{count} chiamata a strumento", other: "{count} chiamate a strumenti" },
    toolError: "Errore",
    toolInput: "Input",
    toolResult: "Risultato",
    noVersionsTitle: "Ancora niente da provare",
    noVersionsDescription: "Applica le modifiche per preparare il primo aggiornamento dell'assistente, poi parla con lui qui.",
    errors: {
      service: "Il modello linguistico non è disponibile in questo momento. Riprova tra un minuto.",
    },
  },
};
