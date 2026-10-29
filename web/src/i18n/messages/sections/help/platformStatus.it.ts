/** `platformStatus.*` texts of the public status page and the announcement banner, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { platformStatusEn } from "./platformStatus.en";

export const platformStatusIt: Translation<typeof platformStatusEn> = {
  title: "Stato della piattaforma",
  description: "Se chat con i clienti, canali, chiamate e pannello funzionano in questo momento, e com'è andata negli ultimi 90 giorni.",
  overall: {
    operational: "Tutto funziona",
    maintenance: "Manutenzione programmata in corso",
    degraded: "Alcune parti sono più lente del solito",
    outage: "Alcune parti al momento non funzionano",
    no_data: "Ancora nessuna misurazione",
  },
  levels: {
    operational: "Funziona",
    maintenance: "Manutenzione",
    degraded: "Lento",
    outage: "Non funziona",
    no_data: "Nessun dato",
  },
  components: {
    chat: "Chat del sito e pagina chat",
    meta: "WhatsApp, Instagram e Messenger",
    telegram: "Telegram",
    voice: "Chiamate",
    cabinet: "Pannello e accesso",
  },
  checkedAt: "Verificato: {time}",
  monitoringDelayed: {
    title: "Le verifiche interne della piattaforma sono in ritardo",
    minutesAgo: {
      one: "L'ultima verifica risale a {count} minuto fa.",
      other: "L'ultima verifica risale a {count} minuti fa.",
    },
    at: "Ultima verifica: {time}",
    body: "Finché le verifiche non tornano in pari, nessuno può garantire i livelli qui sotto, quindi le chat vengono mostrate come più lente.",
  },
  componentsTitle: "Parti della piattaforma",
  historyLabel: "{component}: gli ultimi 90 giorni",
  historyStart: "90 giorni fa",
  historyEnd: "Oggi",
  uptime: {
    one: "{share} senza problemi in {count} giorno",
    other: "{share} senza problemi in {count} giorni",
  },
  observingSince: "Monitorato dal {date}",
  noHistory: "Ancora nessun giorno misurato",
  day: "{day}: {level}",
  announcementLevels: {
    info: "Comunicazione",
    maintenance: "Manutenzione",
    degraded: "Rallentamenti",
    outage: "Interruzione",
  },
  activeTitle: "In corso",
  scheduled: "Programmato",
  starts: "Inizio: {time}",
  since: "Iniziato: {time}",
  expectedEnd: "Fine prevista: {time}",
  resolved: "Risolto: {time}",
  updated: "Aggiornato: {time}",
  affects: "Riguarda: {components}",
  pastTitle: "Incidenti passati",
  pastEmpty: "Nessun incidente negli ultimi 90 giorni.",
  unreachable: {
    title: "Impossibile caricare lo stato",
    body: "Al momento questa pagina non riesce a raggiungere la piattaforma. Se anche le chat non funzionano, scrivi all'assistenza: il team ne è già al corrente.",
  },
  selfMeasured: "La piattaforma si verifica da sola ogni cinque minuti; il team aggiunge ciò che sa.",
  openCabinet: "Apri il pannello",
  banner: {
    region: "Avviso della piattaforma",
    details: "Dettagli",
    dismiss: "Nascondi",
  },
};
