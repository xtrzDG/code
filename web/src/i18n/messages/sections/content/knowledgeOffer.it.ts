/** `knowledgeOffer.*` in Italian: services, rooms and seasonal rates (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { knowledgeOfferEn } from "./knowledgeOffer.en";

export const knowledgeOfferIt: Translation<typeof knowledgeOfferEn> = {
  offer: {
    nightlyPrice: "Tariffa per notte, {currency}",
    nightlyPriceHint: "Le notti fuori da ogni stagione costano questo importo. Lascia vuoto se dipende da qualcosa.",
    durationHint: "Da 5 a 720 minuti: una prenotazione dura questo tempo.",
    buffer: "Pausa dopo, min",
    bufferHint: "Chi lo esegue resta occupato per questo tempo dopo (pulizia, preparazione).",
    performers: "Chi lo esegue",
    performersHint: "Vengono proposti solo loro. Nessuno selezionato: può farlo chiunque non sia legato a un servizio specifico.",
    rooms: "Camere di questo tipo",
    roomsHint: "Un soggiorno di questo tipo si prenota in una di queste camere. Nessuna selezionata: qualsiasi camera prenotata a notte.",
    noResources: "Ancora nessuno da scegliere: aggiungi prima le persone o i luoghi prenotati a tempo.",
    noRooms: "Ancora nessuna camera prenotata a notte: aggiungile prima.",
    toResources: "Apri Risorse e orari",
    resourceOff: "disattivata",
    filter: "Cerca per nome",
    noMatches: "Nessun risultato per “{query}”",
    selectedCount: { one: "{count} selezionato", other: "{count} selezionati" },
    seasons: "Tariffe stagionali",
    seasonsHint: "Una notte all'interno di una stagione costa la sua tariffa, ogni anno. Una stagione può scavalcare il Capodanno; le stagioni non possono sovrapporsi.",
    addSeason: "Aggiungi una stagione",
    seasonTitle: "Stagione {number}",
    seasonName: "Nome",
    seasonNamePlaceholder: "Per esempio: Estate",
    from: "Dal",
    to: "Al",
    day: "Giorno",
    month: "Mese",
    seasonRate: "Per notte, {currency}",
    removeSeason: "Rimuovi la stagione {number}",
    noSeasons: "Nessuna stagione: ogni notte costa la tariffa per notte.",
    performedBy: "Con {names}",
    roomsList: "Camere: {names}",
    breakValue: "+{count} min di pausa",
    perNight: "{price} a notte",
    seasonsValue: { one: "{count} stagione", other: "{count} stagioni" },
    errors: {
      bufferRange: "Da 0 a 240 minuti",
      seasonDate: "Quel mese non ha questo giorno",
      seasonOverlap: "Le stagioni {first} e {second} hanno giorni in comune: una notte deve avere una sola tariffa.",
      tooManySeasons: { one: "Al massimo {count} stagione", other: "Al massimo {count} stagioni" },
    },
  },
};
