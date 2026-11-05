/** `channelPages.*` texts of the Channels pages on a phone, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { channelPagesEn } from "./channelPages.en";

export const channelPagesIt: Translation<typeof channelPagesEn> = {
  heading: "Configura",
  back: "Tutti i canali",
  website: {
    title: "Chat del sito",
    hint: "Colore, pulsante, il codice per il tuo sito e dove può comparire",
  },
  calls: {
    title: "Inoltro di chiamata",
    hint: "I codici che inoltrano all'assistente le chiamate che perdi",
  },
  share: {
    title: "Condividi",
    hint: "Link, un codice QR e un cartoncino da tavolo",
  },
  off: {
    website: "La chat del sito è disattivata. Attivala tra i canali per sceglierne l'aspetto e metterla sul tuo sito.",
    calls: "Il canale telefonico non è collegato. Collegalo tra i canali per ottenere i codici di inoltro.",
  },
};
