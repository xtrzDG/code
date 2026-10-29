/** `adminReplySpeed.*` texts of the reply-speed card on the platform admin's client page, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminReplySpeedEn } from "./adminReplySpeed.en";

export const adminReplySpeedIt: Translation<typeof adminReplySpeedEn> = {
  title: "Velocità di risposta, 7 giorni",
  description: "Quanto hanno atteso i clienti, dal primo messaggio senza risposta alla risposta dell'assistente.",
  median: "Attesa tipica (mediana)",
  p95: "19 risposte su 20 entro",
  replies: "Risposte misurate",
  slowNote: "Più di una risposta su venti ha richiesto oltre 15 secondi. Controlla il fornitore del modello e gli strumenti dell'attività.",
  empty: "Nessuna risposta misurata negli ultimi 7 giorni. Le chat vengono misurate da questo rilascio in poi; le chiamate e la chat di prova no.",
  tableCaption: "Velocità di risposta per canale",
  channel: "Canale",
  channelReplies: "Risposte",
  channelMedian: "Mediana",
  channelP95: "95%",
  seconds: "{value} s",
  minutes: "{value} min",
  issueLabel: "Risposte lente",
};
