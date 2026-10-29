/** `coachMarks.*` texts of the one-time tips, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { coachMarksEn } from "./coachMarks.en";

export const coachMarksIt: Translation<typeof coachMarksEn> = {
  label: "Suggerimento",
  gotIt: "Ho capito",
  readGuide: "Leggi la guida",
  inbox: {
    title: "Le conversazioni del tuo team",
    body: "Le conversazioni che richiedono una persona vengono prima. Aprine una per rispondere, assegnarla a un collega o lasciare una nota visibile solo al team.",
  },
  assistant: {
    title: "Prova qui il tuo assistente, prima di tutto",
    body: "Scrivi come farebbe un cliente. Ciò che insegni all'assistente compare qui prima di arrivare ai clienti.",
  },
  channels: {
    title: "Collegati dove ti scrivono i clienti",
    body: "Inizia dal canale che i tuoi clienti usano di più. Ogni scheda indica se funziona e quando è arrivato l'ultimo messaggio.",
  },
};
