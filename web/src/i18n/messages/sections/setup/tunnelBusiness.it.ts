/** `tunnelBusiness.*` texts of the tunnel's first two steps, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { tunnelBusinessEn } from "./tunnelBusiness.en";

export const tunnelBusinessIt: Translation<typeof tunnelBusinessEn> = {
  business: {
    title: "Come si chiama la tua attività?",
    text: "Creeremo un assistente che risponde ai tuoi clienti al posto tuo, giorno e notte.",
    name: "Nome dell'attività",
    namePlaceholder: "Ad esempio, Salone Aurora",
    kindTitle: "Di cosa ti occupi?",
    kindHint: "Scegli la voce più vicina. Determina cosa chiede, prenota e sa il tuo assistente.",
    kindFixed: "L'hai scelto quando hai creato l'assistente; non si può cambiare.",
    legalReview: "Le attività di questo tipo passano una breve verifica legale prima che l'assistente vada online.",
    detailsTitle: "Un'ultima cosa che i clienti chiedono sempre",
    errors: {
      name: "Scrivi il nome della tua attività.",
      kind: "Scegli di cosa si occupa la tua attività.",
    },
  },
  place: {
    title: "Dove ti trovi?",
    text: "Il paese determina la valuta, il fuso orario e le lingue dei tuoi clienti. Abbiamo compilato quello che potevamo.",
    country: "Paese",
    countryHint: "Prezzi in {currency}",
    countryFixed: "Il paese non si può cambiare dopo la creazione dell'assistente.",
    city: "Città",
    cityPlaceholder: "Ad esempio, Milano",
    address: "Indirizzo",
    addressPlaceholder: "Via e numero civico",
    addressHint: "L'assistente spiega ai clienti come trovarti.",
    addressOptional: "facoltativo",
    languages: "Lingue in cui scrivono i tuoi clienti",
    languagesHint: "L'assistente risponde a ogni cliente nella sua lingua, tra queste.",
    defaultLanguage: "Primo saluto in",
    timezone: "Fuso orario",
    creating: "Creazione del tuo assistente…",
    errors: {
      country: "Scegli il tuo paese.",
      city: "Scrivi la tua città: dice ai clienti e all'assistente dove sei.",
      languages: "Scegli almeno una lingua.",
      address: "Scrivi il tuo indirizzo: i clienti ne hanno bisogno per trovarti.",
      restricted: "Non è ancora possibile creare attività di questo paese.",
    },
  },
};
