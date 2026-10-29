/** `publicPricing.*` texts of prices on the public site, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { publicPricingEn } from "./publicPricing.en";

export const publicPricingIt: Translation<typeof publicPricingEn> = {
  converted: "{price} al mese nella tua valuta",
  billedIn: "I piani per questo paese sono fatturati in {currency}.",
  conversionNote: "Gli importi con ≈ sono solo indicativi: convertiti dagli euro secondo {source}, in data {date}; paghi in euro.",
  rateSources: {
    nbg: "il tasso ufficiale della Banca nazionale della Georgia",
    ecb: "il tasso di riferimento della Banca centrale europea",
    official: "i tassi ufficiali delle banche centrali",
    planning: "il tasso di pianificazione della piattaforma (non un tasso bancario)",
  },
  setup: {
    title: "Configuralo tu o lascia fare a noi",
    subtitle: "L'assistente è lo stesso in entrambi i casi. Scegli al momento dell'abbonamento.",
    selfTitle: "In autonomia",
    selfPrice: "Gratis",
    selfPoints: {
      guide: "Una guida in otto brevi passaggi, con risposte pronte per il tuo settore",
      test: "Una chat di prova e verifiche automatiche prima dell'attivazione",
      channels: "Colleghi i canali con un aiuto passo dopo passo",
    },
    doneTitle: "Ci pensiamo noi",
    donePrice: "{price} una tantum",
    donePoints: {
      knowledge: "Inseriamo prezzi, menù e regole partendo dal tuo sito o dai tuoi file",
      channels: "Colleghiamo i tuoi canali e l'inoltro di chiamata",
      launch: "Proviamo l'assistente con te e lo attiviamo insieme",
    },
  },
  testimonials: {
    title: "Cosa dicono i titolari",
  },
};
