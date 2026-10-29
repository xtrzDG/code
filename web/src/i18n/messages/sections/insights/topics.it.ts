/** `topics.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { topicsEn } from "./topics.en";

export const topicsIt: Translation<typeof topicsEn> = {
  title: "Cosa chiedono i clienti",
  description: "I primi messaggi degli ultimi 30 giorni, raggruppati per argomento ogni notte.",
  updated: "Raggruppati il {date}",
  waiting: "Gli argomenti compaiono dopo la prima notte con conversazioni.",
  empty: "Negli ultimi 30 giorni non ha ancora scritto nessun cliente.",
  conversations: { one: "{count} conversazione", other: "{count} conversazioni" },
  unanswered: { one: "{count} senza risposta", other: "{count} senza risposta" },
  unansweredHint: "Domande a cui l'assistente non ha saputo rispondere: aggiungi una risposta e ci riuscirà.",
  addAnswer: "Aggiungi una risposta",
  otherLanguages: "Altre lingue",
  otherTopic: "Altre domande",
  languageLabel: "Lingua",
  loading: "Caricamento degli argomenti…",
};
