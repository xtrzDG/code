/** `tunnelOffer.*` texts of the offer, hours and bookings steps, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { tunnelOfferEn } from "./tunnelOffer.en";

export const tunnelOfferIt: Translation<typeof tunnelOfferEn> = {
  offer: {
    title: "Cosa offri?",
    text: "Aggiungi cosa vendi, con i prezzi. L'assistente indica solo i prezzi presenti qui.",
    sourcesLabel: "Come aggiungerli",
    sources: {
      type: "Inseriscili a mano",
      website: "Dal tuo sito web",
      menu: "Da una foto o un file del menù",
    },
    tableLabel: "La tua offerta",
    name: "Nome",
    namePlaceholder: "Cosa i clienti possono ordinare o prenotare",
    price: "Prezzo, {currency}",
    pricePlaceholder: "0",
    suggestion: "Esempio",
    suggestionsHint: "Gli esempi vengono salvati solo quando indichi un prezzo. Rimuovi quelli che non offri.",
    addRow: "Aggiungi una riga",
    removeRow: "Rimuovi {name}",
    removeEmpty: "Rimuovi questa riga",
    rowMenu: "Altro per {name}",
    rowSaving: "Salvataggio…",
    rowSaved: "Salvato",
    rowFailed: "Non salvato",
    priced: {
      one: "{count} voce con prezzo",
      other: "{count} voci con prezzo",
    },
    importedTitle: {
      one: "{count} voce aggiunta dall'importazione",
      other: "{count} voci aggiunte dall'importazione",
    },
    importHint: "Lo leggiamo e ti mostriamo cosa abbiamo trovato. Non salviamo nulla prima che tu lo controlli.",
  },
  hours: {
    title: "Quali sono i tuoi orari?",
    text: "Abbiamo proposto gli orari tipici per il tuo tipo di attività. Modifica ciò che è diverso.",
    hoursLabel: "Orari di apertura",
    bookingsTitle: "Come funzionano le prenotazioni?",
    slot: "Una visita dura",
    partySize: "Numero massimo di persone per prenotazione",
    notice: "Prenotare con almeno",
    noticeNone: "Nessun preavviso necessario",
    cancellation: "Regola di cancellazione",
    cancellationHint: "I clienti la ricevono quando prenotano o cancellano.",
    resourceTitle: "Cosa prenotano i clienti",
    resourceHint: "Puoi aggiungerne altri in seguito in Assistente → Conoscenze.",
    resourceName: "Nome",
    resourceCount: "Quanti",
    resourceCapacity: "Persone per ciascuno",
    minutes: {
      one: "{count} minuto",
      other: "{count} minuti",
    },
    hoursCount: {
      one: "{count} ora",
      other: "{count} ore",
    },
    noticeHours: {
      one: "{count} ora di anticipo",
      other: "{count} ore di anticipo",
    },
    noticeDays: {
      one: "{count} giorno di anticipo",
      other: "{count} giorni di anticipo",
    },
    noticeMinutes: {
      one: "{count} minuto di anticipo",
      other: "{count} minuti di anticipo",
    },
    errors: {
      noHours: "Indica almeno un giorno di apertura.",
      partySize: "Scrivi un numero intero, a partire da 1.",
      resourceName: "Indica cosa prenotano i clienti.",
      capacity: "Scrivi un numero intero, a partire da 1.",
      unitCount: "Scrivi un numero intero, a partire da 1.",
    },
  },
};
