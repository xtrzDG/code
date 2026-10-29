/** `adminStatus.*` texts of the admin's status announcements, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminStatusEn } from "./adminStatus.en";

export const adminStatusIt: Translation<typeof adminStatusEn> = {
  title: "Avvisi della pagina di stato",
  description: "Cosa dicono la pagina di stato pubblica e il banner in cima a ogni pannello. Ogni modifica finisce nel registro attività.",
  create: "Nuovo avviso",
  openPage: "Apri la pagina di stato",
  none: "Ancora nessun avviso",
  noneDescription: "Scrivine uno quando una parte della piattaforma non funziona, è lenta o sta per andare in manutenzione.",
  status: {
    active: "Attivo",
    resolved: "Risolto",
  },
  edit: "Aggiorna",
  resolve: "Risolvi",
  resolveTitle: "Segnare questo avviso come risolto?",
  resolveBody: "Il banner scompare da tutti i pannelli e la pagina di stato lo elenca tra gli incidenti passati.",
  published: "Avviso pubblicato",
  saved: "Avviso aggiornato",
  resolvedToast: "Avviso risolto",
  form: {
    createTitle: "Nuovo avviso",
    editTitle: "Aggiorna l'avviso",
    description: "I titolari lo vedono subito sulla pagina di stato e in cima al loro pannello.",
    level: "Livello",
    levelHints: {
      info: "Una comunicazione: nessuna parte della piattaforma risulta coinvolta.",
      maintenance: "Interventi programmati: indica un orario di inizio per annunciarli in anticipo.",
      degraded: "Funziona, ma più lentamente o con alcuni errori.",
      outage: "Non funziona. I titolari non possono nascondere questo banner.",
    },
    components: "Parti coinvolte",
    componentsHint: "Finché l'avviso è attivo, ogni parte scelta mostra questo livello sulla pagina di stato.",
    textLabel: "Testo in {language}",
    textHint: "L'inglese è obbligatorio. I titolari la cui lingua è lasciata vuota leggono il testo in inglese.",
    startsAt: "Inizio",
    startsAtHint: "Vuoto: adesso. Un orario successivo annuncia interventi programmati.",
    expectedEnd: "Fine prevista",
    timeZone: "Gli orari sono nel fuso orario di questo dispositivo.",
    publish: "Pubblica",
    save: "Salva",
    saving: "Salvataggio…",
    errors: {
      textRequired: "Scrivi il testo in inglese: almeno 3 caratteri.",
      textShort: "Almeno 3 caratteri, oppure lascialo vuoto.",
      componentsRequired: "Scegli almeno una parte coinvolta.",
      time: "Inserisci una data e un orario.",
      endBeforeStart: "La fine deve essere successiva all'inizio e nel futuro.",
      startTooLate: "L'inizio può essere al massimo tra 60 giorni.",
    },
  },
};
