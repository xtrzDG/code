/** `tunnel.*` texts of the setup tunnel's frame, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { tunnelEn } from "./tunnel.en";

export const tunnelIt: Translation<typeof tunnelEn> = {
  pageTitle: "Crea un assistente AI",
  newAssistant: "Nuovo assistente",
  railLabel: "Passaggi della configurazione",
  steps: {
    business: "La tua attività",
    place: "Dove ti trovi",
    offer: "Cosa offri",
    hours: "Orari e prenotazioni",
    people: "Chi ti aiuta",
    channels: "Dove scrivono i clienti",
    try: "Provalo",
    launch: "Attivazione",
  },
  stepOf: "Passaggio {number} di {total}",
  stepState: {
    done: "completato",
    skipped: "saltato",
    current: "sei qui",
    todo: "da fare",
  },
  announce: "Passaggio {number} di {total}: {title}",
  announceFinale: "Il tuo assistente è online",
  back: "Indietro",
  continue: "Continua",
  skip: "Salta per ora",
  enterHint: "oppure premi Invio",
  exit: "Salva ed esci",
  saving: "Salvataggio…",
  saved: "Salvato",
  saveFailed: "Non ancora salvato",
  ownerOnlyTitle: "Il titolare sta creando l'assistente",
  ownerOnlyText: "Solo un titolare di {business} può configurarlo. Conversazioni, prenotazioni e richieste compariranno nel pannello quando sarà online.",
  openCabinet: "Apri il pannello",
};
