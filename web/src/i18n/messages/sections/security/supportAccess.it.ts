/** `supportAccess.*` texts of platform support in a cabinet, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { supportAccessEn } from "./supportAccess.en";

export const supportAccessIt: Translation<typeof supportAccessEn> = {
  label: "Accesso dell'assistenza della piattaforma",
  owner: {
    title: "L'assistenza della piattaforma sta consultando il tuo pannello",
    who: "{name}: “{reason}”",
    reason: "Motivo: “{reason}”",
    until: "fino alle {time}",
    readOnly: "L'assistenza può solo consultare; senza di te non si può modificare nulla.",
    end: "Termina l'accesso",
    endTitle: "Terminare l'accesso dell'assistenza della piattaforma?",
    endDescription:
      "L'assistenza esce subito dal tuo pannello e anche il suo permesso di apportare modifiche termina.",
    ended: "L'assistenza della piattaforma non ha più accesso",
    allow: "Consenti modifiche all'assistenza",
    allowHint:
      "Ad esempio, se le hai chiesto di configurare l'assistente per te. Scade automaticamente.",
    allowedUntil: "L'assistenza può apportare modifiche fino alle {time}",
    hours: "Per quanto tempo",
    hourOptions: {
      one: "{count} ora",
      other: "{count} ore",
    },
    dayOption: "Un giorno",
    weekOption: "Una settimana",
    allowed: "L'assistenza può apportare modifiche",
    stopped: "L'assistenza può di nuovo solo consultare",
    staff: "Solo un titolare può terminare l'accesso o consentire modifiche all'assistenza.",
  },
  support: {
    title: "Stai consultando {name} come assistenza della piattaforma",
    readOnly: "Sola lettura: le modifiche vengono rifiutate.",
    canWrite: "Modifiche consentite dal titolare fino alle {time}",
    until: "L'accesso termina alle {time}",
    leave: "Esci dal pannello",
    left: "Hai lasciato il pannello",
  },
};
