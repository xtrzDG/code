/** `knowledgeOffer.*` in German: services, rooms and seasonal rates (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { knowledgeOfferEn } from "./knowledgeOffer.en";

export const knowledgeOfferDe: Translation<typeof knowledgeOfferEn> = {
  offer: {
    nightlyPrice: "Preis pro Nacht, {currency}",
    nightlyPriceHint: "Nächte außerhalb jeder Saison kosten so viel. Leer lassen, wenn es von etwas abhängt.",
    durationHint: "5 bis 720 Minuten: so lange dauert eine Buchung.",
    buffer: "Pause danach, Min.",
    bufferHint: "Wer die Leistung erbringt, bleibt danach so lange belegt (Reinigung, Vorbereitung).",
    performers: "Wer sie erbringt",
    performersHint: "Nur diese werden dafür angeboten. Niemand angehakt: Jeder, der nicht an eine bestimmte Leistung gebunden ist, kann sie erbringen.",
    rooms: "Zimmer dieses Typs",
    roomsHint: "Ein Aufenthalt dieses Typs wird in einem dieser Zimmer gebucht. Keines angehakt: jedes Zimmer, das pro Nacht gebucht wird.",
    noResources: "Noch niemand zur Auswahl: Fügen Sie zuerst die Personen oder Orte hinzu, die nach Zeit gebucht werden.",
    noRooms: "Noch keine Zimmer, die pro Nacht gebucht werden: Fügen Sie sie zuerst hinzu.",
    toResources: "Ressourcen und Zeiten öffnen",
    resourceOff: "aus",
    filter: "Nach Namen suchen",
    noMatches: "Niemand passt zu „{query}“",
    selectedCount: { one: "{count} gewählt", other: "{count} gewählt" },
    seasons: "Saisonpreise",
    seasonsHint: "Eine Nacht innerhalb einer Saison kostet deren Preis, jedes Jahr. Eine Saison darf über Neujahr gehen; Saisons dürfen sich nicht überschneiden.",
    addSeason: "Saison hinzufügen",
    seasonTitle: "Saison {number}",
    seasonName: "Name",
    seasonNamePlaceholder: "Zum Beispiel: Sommer",
    from: "Von",
    to: "Bis",
    day: "Tag",
    month: "Monat",
    seasonRate: "Pro Nacht, {currency}",
    removeSeason: "Saison {number} entfernen",
    noSeasons: "Keine Saisons: Jede Nacht kostet den Preis pro Nacht.",
    performedBy: "Mit {names}",
    roomsList: "Zimmer: {names}",
    breakValue: "+{count} Min. Pause",
    perNight: "{price} pro Nacht",
    seasonsValue: { one: "{count} Saison", other: "{count} Saisons" },
    errors: {
      bufferRange: "0 bis 240 Minuten",
      seasonDate: "Diesen Tag gibt es in dem Monat nicht",
      seasonOverlap: "Die Saisons {first} und {second} teilen sich Tage: Eine Nacht muss einen Preis haben.",
      tooManySeasons: "Höchstens {count} Saisons",
    },
  },
};
