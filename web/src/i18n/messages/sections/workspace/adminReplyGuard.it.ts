/** `adminReplyGuard.*` texts of the reply-guard card on the platform admin's client page, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminReplyGuardEn } from "./adminReplyGuard.en";

export const adminReplyGuardIt: Translation<typeof adminReplyGuardEn> = {
  title: "Controllo delle risposte, 7 giorni",
  description:
    "Risposte bloccate dal controllo perché cifre, affermazioni o contatti non trovavano riscontro nei dati dell'attività, e messaggi che hanno cercato di cambiare le istruzioni dell'assistente.",
  checked: "Risposte controllate",
  heldBack: "Bloccate",
  heldBackShare: "{share} delle risposte",
  rewritten: "Riscritte una volta",
  handedOff: "Passate al personale",
  injectionFlags: "Tentativi di injection",
  heldBackNote:
    "Il controllo ha bloccato almeno una risposta su sei. Verifica i dati e i prezzi dell'attività: all'assistente manca qualcosa che i clienti chiedono.",
  probedNote:
    "Qualcuno continua a cercare di cambiare le istruzioni dell'assistente. Dopo tre tentativi il contatto viene fermato per un giorno; dai un'occhiata alle conversazioni.",
  empty: "Nessuna risposta controllata negli ultimi 7 giorni.",
  issueLabel: "Picco di risposte bloccate",
};
