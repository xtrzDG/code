/** `privacyRetention.*` texts of Settings → Privacy → "How long data is kept", in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { privacyRetentionEn } from "./privacyRetention.en";

export const privacyRetentionIt: Translation<typeof privacyRetentionEn> = {
  title: "Per quanto tempo conserviamo i dati",
  description:
    "I dati dei clienti vengono cancellati automaticamente allo scadere di questi periodi. L'informativa sulla privacy della tua chat ospitata comunica ai clienti gli stessi periodi.",
  conversations: {
    label: "Conversazioni",
    hint: "Calcolato dall'ultimo messaggio di una conversazione. Poi vengono cancellati i suoi messaggi, le note del team, le trascrizioni e le registrazioni delle chiamate; prenotazioni, lead e richieste conservano solo ciò che non è personale.",
  },
  modelRecords: {
    label: "Registri delle elaborazioni AI dell'assistente",
    hint: "Il testo esatto inviato al modello AI, conservato per verificare le risposte. Viene cancellato qui e nel registro della qualità (Langfuse). Al massimo 30 giorni.",
  },
  periods: {
    days: { one: "{count} giorno", other: "{count} giorni" },
    months: { one: "{count} mese", other: "{count} mesi" },
    years: { one: "{count} anno", other: "{count} anni" },
    recommended: "{period} (consigliato)",
    maximum: "{period} (massimo)",
  },
  recordings: "Le registrazioni delle chiamate sono conservate per {period}.",
  changeRecordings: "Modifica in Generale",
  processorsTitle: "Copie presso i nostri sub-responsabili del trattamento",
  processors: {
    langfuse: "Langfuse: i log delle elaborazioni AI dell'assistente",
    elevenlabs: "ElevenLabs: le chiamate (audio e trascrizione)",
  },
  processorsDeleted: "vengono cancellate insieme alle nostre, secondo questi periodi e quando cancelli i dati di un cliente:",
  processorsNone:
    "Langfuse ed ElevenLabs non sono usati su questa piattaforma, quindi non conservano copie dei dati dei tuoi clienti.",
  messagingApps:
    "Le chat su WhatsApp, Messenger, Instagram e Telegram restano nell'app del cliente: quelle piattaforme permettono solo al cliente di cancellarle.",
  lastCleanupTitle: "Ultima pulizia",
  lastCleanup: "{date}",
  nothingDue: "Non c'era nulla da cancellare.",
  noCleanupYet: "La prima pulizia viene eseguita stanotte.",
  removed: { one: "{count} record rimosso", other: "{count} record rimossi" },
  counts: {
    deleted_messages: "messaggi",
    deleted_llm_turns: "registri delle elaborazioni AI",
    deleted_notes: "note del team",
    deleted_media: "file dei clienti",
    deleted_missed_calls: "chiamate perse",
    erased_calls: "chiamate",
    anonymized_leads: "lead",
    anonymized_bookings: "prenotazioni",
    anonymized_handoffs: "richieste",
  },
  shorterTitle: "Cancellare stanotte i dati più vecchi?",
  shorterDescription:
    "Con periodi più brevi, la pulizia di stanotte cancella definitivamente tutto ciò che li supera (conversazioni: {conversations}; registri delle elaborazioni AI: {modelRecords}). L'operazione non si può annullare.",
  shorterConfirm: "Accorcia e cancella",
  qualitySampling: {
    label: "Verifiche di qualità sulle conversazioni reali",
    hint: "Ogni notte un piccolo campione di conversazioni concluse (escluse le chat di prova) viene valutato dallo stesso fornitore AI che scrive le risposte, così le risposte deboli emergono nella qualità dell'assistente. Disattivalo per escludere le conversazioni dei tuoi clienti da queste verifiche.",
  },
};
