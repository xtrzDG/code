/** `live.*` texts of the live cabinet, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { liveEn } from "./live.en";

export const liveIt: Translation<typeof liveEn> = {
  status: {
    live: "In tempo reale",
    connecting: "Connessione…",
    reconnecting: "Riconnessione…",
    paused: "Aggiornamenti in tempo reale in pausa",
  },
  updatedJustNow: "Aggiornato ora",
  updatedMinutesAgo: {
    one: "Aggiornato {count} minuto fa",
    other: "Aggiornato {count} minuti fa",
  },
  updatedAt: "Aggiornato alle {time}",
  updating: "Aggiornamento…",
  liveHint: "Questa pagina si aggiorna da sola quando i clienti scrivono, prenotano o hanno bisogno di una persona.",
  reconnectingHint: "La connessione si è interrotta e continuiamo a riprovare. Puoi anche riprovare subito.",
  reconnect: "Riprova ora",
  needsPersonTitle: "Un cliente ha bisogno di una persona",
  needsPersonOpen: "Apri",
  sound: "Suono quando qualcuno ha bisogno di una persona",
  soundHint: "Un breve suono su questo dispositivo quando una conversazione passa al tuo team.",
};
