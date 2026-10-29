/** `setup.*` texts of creating the assistant before it exists, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { setupEn } from "./setup.en";

export const setupIt: Translation<typeof setupEn> = {
  navEntry: "Crea un assistente AI",
  navEntryHint: "Passo dopo passo, circa 20 minuti",
  eyebrow: "{business}",
  title: "Creiamo il tuo assistente AI",
  description:
    "Raccontaci della tua attività in pochi semplici passaggi. Prepareremo un assistente che risponde ai tuoi clienti giorno e notte, prende le prenotazioni e ti chiama quando serve una persona.",
  start: "Crea un assistente AI",
  continue: "Continua la creazione",
  progress: { one: "{done} su {total} passaggio completato", other: "{done} su {total} passaggi completati" },
  duration: "Circa 20 minuti. Puoi fermarti e riprendere quando vuoi.",
  stagesLabel: "Come funziona",
  stages: {
    business: {
      title: "Racconta la tua attività",
      description: "Contatti, orari di apertura e cosa offri.",
    },
    rules: {
      title: "Insegnagli le tue regole",
      description: "Prenotazioni, risposte alle domande frequenti e quando chiamarti.",
    },
    meet: {
      title: "Conosci il tuo assistente",
      description: "Provalo in chat, poi attivalo per i tuoi clienti.",
    },
  },
  staffTitle: "L'assistente è in fase di creazione",
  staffDescription:
    "Il titolare di {business} lo sta configurando. Conversazioni, prenotazioni e richieste compariranno qui appena sarà pronto.",
};
