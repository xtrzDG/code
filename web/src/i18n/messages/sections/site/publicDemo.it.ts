/** `publicDemo.*` texts of the landing page's live demo chat, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { publicDemoEn } from "./publicDemo.en";

export const publicDemoIt: Translation<typeof publicDemoEn> = {
  label: "Demo dal vivo dell'assistente",
  badge: "Demo dal vivo",
  sampleBadge: "Esempio",
  sandbox: "Ambiente di prova: nessuna prenotazione è reale",
  pick: "Settore",
  place: "{niche} · {city}",
  greeting: "Ciao! Sono l'assistente AI di {business}. Chiedimi quello che chiederebbero i tuoi clienti: prezzi, orari di apertura, una prenotazione.",
  starters: "Prova a chiedere",
  genericStarters: {
    hours: "Quali sono i vostri orari di apertura?",
    prices: "Quanto costa?",
    place: "Dove vi trovate?",
  },
  inputLabel: "Il tuo messaggio all'assistente demo",
  placeholder: "Scrivi come farebbe un cliente…",
  send: "Invia",
  typing: "L'assistente sta scrivendo…",
  restart: "Ricomincia",
  you: "Tu",
  assistant: "Assistente",
  outcomes: {
    booking: "Qui verrebbe creata una prenotazione",
    request: "Qui la richiesta arriverebbe al tuo responsabile",
    handoff: "Qui la conversazione passerebbe a una persona",
  },
  messagesLeft: {
    one: "Ti resta {count} messaggio in quest'ora",
    other: "Ti restano {count} messaggi in quest'ora",
  },
  failures: {
    limit: "La demo ha ricevuto molti messaggi. Riprova tra poco oppure crea il tuo assistente: ci vogliono circa dieci minuti.",
    unavailable: "Questa demo al momento è in pausa. Prova un altro settore.",
    offline: "Nessuna connessione. Controlla internet e riprova.",
    failed: "Il messaggio non è stato inviato. Riprova.",
  },
  privacy: "Demo pubblica: non condividere dati personali.",
  cta: "Crea il mio",
};
