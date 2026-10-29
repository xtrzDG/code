/** `quality.*` texts of production quality (the nightly judge's scores), in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { qualityEn } from "./quality.en";

export const qualityIt: Translation<typeof qualityEn> = {
  admin: {
    title: "Qualità delle conversazioni, 30 giorni",
    description: "Ogni notte un giudice AI valuta un piccolo campione di conversazioni reali secondo i cinque criteri di verifica. Solo punteggi, nessun testo dei clienti.",
    empty: "Nessuna conversazione valutata negli ultimi 30 giorni.",
    average: "Media, 30 giorni",
    lastWeek: "Ultimi 7 giorni",
    previousWeek: "7 giorni prima: {score}",
    judged: "Conversazioni valutate",
    dropping: "In calo del {percent}%",
    droppingNote: "L'ultima settimana ha ottenuto un punteggio inferiore del {percent}% rispetto alla precedente. Apri qui sotto le conversazioni con il punteggio più basso e l'ultimo aggiornamento del cliente.",
    scoreValue: "{score} / 5",
    trendLabel: "Punteggio medio al giorno, ultimi 30 giorni",
    noScoresDay: "{date}: nessuna valutazione",
    dayValue: "{date}: {score} / 5 su {count}",
    showTable: "Mostra come tabella",
    day: "Giorno",
    count: "Valutate",
    lowestTitle: "Conversazioni con il punteggio più basso",
    lowestCaption: "I cinque punteggi più bassi degli ultimi 30 giorni",
    judgedAt: "Valutata",
    channel: "Canale",
    language: "Lingua",
    score: "Punteggio",
    weak: "Punti deboli",
    noWeak: "Nessuno sotto 4",
  },
  conversation: {
    title: "Punteggio del giudice AI",
    description: "Questa conversazione era nel campione notturno di qualità.",
    judgedAt: "Valutata il {date}",
    notes: "Note",
  },
};
