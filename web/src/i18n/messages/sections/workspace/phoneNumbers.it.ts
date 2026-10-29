/** `phoneNumbers.*` texts of a phone number rented from the platform, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { phoneNumbersEn } from "./phoneNumbers.en";

export const phoneNumbersIt: Translation<typeof phoneNumbersEn> = {
  panel: {
    noNumber: "Non hai ancora un numero di telefono per le chiamate? Prendine uno da noi: risponde subito con il tuo assistente.",
    getNumber: "Ottieni un numero",
    rentedTitle: "Il tuo numero fornito da noi",
    monthly: "{price} al mese",
    answering: "Risponde con il tuo assistente",
    connecting: "Collegamento al tuo assistente…",
    waitsForPublish: "Non risponde ancora: pubblica il tuo assistente con le chiamate attive e risponderà su questo numero.",
    releasing: "Restituzione in corso",
    giveBackHint: "Per restituire il numero, scollega il canale telefonico. Non viene più addebitato e torna all'operatore.",
    requestTitle: "Numero richiesto",
    requestText: "Un numero {type} in {country}. Il nostro team se ne occupa e ti scrive; può richiedere qualche giorno lavorativo.",
    requestTextCity: "Un numero {type} in {country}, vicino a {city}. Il nostro team se ne occupa e ti scrive; può richiedere qualche giorno lavorativo.",
    cancelRequest: "Annulla la richiesta",
    requestCancelled: "Richiesta annullata",
    ownerOnly: "Solo un titolare può prendere un numero.",
    loading: "Caricamento del tuo numero di telefono…",
    disconnectReleases: "Quando scolleghi, {number} torna all'operatore in modo definitivo: non viene più addebitato e lo stesso numero potrebbe non essere più disponibile.",
  },
  tunnel: {
    title: "Chiamate",
    text: "Prendi un numero da noi e l'assistente risponderà alle chiamate su quel numero, nella lingua dei tuoi clienti. Puoi farlo anche più tardi nella pagina Canali.",
  },
  dialog: {
    title: "Ottieni un numero di telefono",
    description: "Un numero nel paese che scegli, addebitato ogni mese con il tuo piano.",
    country: "Paese",
    countriesNow: "Disponibili subito",
    countriesTeam: "Gestiti dal nostro team",
    type: "Tipo di numero",
    city: "Città o zona",
    cityHint: "Facoltativo: cerchiamo numeri vicini.",
    search: "Cerca numeri",
    searching: "Ricerca dei numeri…",
    close: "Chiudi",
  },
  types: {
    local: "locale",
    mobile: "mobile",
    toll_free: "verde",
  },
  typeOptions: {
    local: "Locale (una linea fissa cittadina)",
    mobile: "Mobile",
    toll_free: "Numero verde",
  },
  offers: {
    title: "Numeri che puoi prendere subito",
    price: "{price} al mese per ciascuno",
    none: "Al momento non ci sono numeri liberi di questo tipo lì. Prova senza città, con un altro tipo, oppure chiedi al nostro team.",
    take: "Prendi",
    takeLabel: "Prendi {number}",
  },
  confirm: {
    title: "Prendere {number}?",
    price: "Costa {price} al mese, addebitati con il tuo piano a partire da oggi.",
    channel: "Diventa il tuo canale telefonico e risponde con il tuo assistente.",
    giveBack: "Puoi restituirlo quando vuoi scollegando il canale telefonico.",
    take: "Prendi il numero",
    back: "Torna all'elenco",
    done: "{number} è tuo",
  },
  request: {
    requires_documents: "In questo paese l'autorità di regolamentazione chiede i documenti della tua attività prima di assegnare un numero. Il nostro team se ne occupa insieme a te.",
    on_request: "Qui il nostro team gestisce manualmente i numeri di questo tipo.",
    ask: "Chiedi al nostro team",
    sent: "Richiesta inviata: il nostro team ti scriverà",
  },
  refusals: {
    numberTaken: "Qualcuno ha appena preso questo numero. Cerca di nuovo e scegline un altro.",
    priceChanged: "Il prezzo di questo tipo di numero è cambiato. Cerca di nuovo per vedere il nuovo prezzo.",
  },
};
