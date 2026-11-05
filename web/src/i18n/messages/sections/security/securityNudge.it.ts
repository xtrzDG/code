/** `securityNudge.*` texts of the owner's second-factor banner, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { securityNudgeEn } from "./securityNudge.en";

export const securityNudgeIt: Translation<typeof securityNudgeEn> = {
  title: "Proteggi i dati dei tuoi clienti: attiva un secondo fattore",
  description:
    "Con una passkey o un'app di autenticazione, un codice di accesso rubato da solo non basta ad aprire il tuo pannello.",
  teamGrew:
    "Il tuo team è cresciuto: più persone possono accedere ai dati dei tuoi clienti. Attiva un secondo fattore.",
  action: "Attiva",
  dismiss: "Non ora",
};
