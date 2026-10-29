/** `providerCircuits.*` texts of the admin System page's provider circuits card, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { providerCircuitsEn } from "./providerCircuits.en";

export const providerCircuitsIt: Translation<typeof providerCircuitsEn> = {
  title: "Circuit breaker dei provider",
  description:
    "Ogni provider attraverso cui inviano i worker ha un circuit breaker. Cinque errori in un minuto lo aprono: i messaggi attendono senza alcuna chiamata, e un tentativo di prova parte 30 s dopo. Ogni provider occupa al massimo metà dei thread di consegna di un worker.",
  none: "Nessun worker ha segnalato i propri circuiti",
  noneDescription: "I worker segnalano i circuiti a ogni heartbeat; un worker di una release precedente non ne segnala.",
  circuit: "Circuito",
  state: "Stato",
  workers: "Worker non chiusi",
  workersOf: "{notClosed} su {total}",
  failures: "Errori, ultimo minuto",
  opened: "Apertura",
  states: {
    closed: "Chiuso",
    half_open: "Nuovo tentativo",
    open: "Aperto",
  },
  providers: {
    meta: "Meta (WhatsApp, Messenger, Instagram)",
    telegram: "Bot di Telegram",
    platform_bot: "Bot della piattaforma",
    twilio_sms: "SMS (Twilio)",
    smtp: "E-mail (SMTP)",
    flitt: "Pagamenti (Flitt)",
    stripe: "Pagamenti (Stripe)",
    elevenlabs: "Voce (ElevenLabs)",
    web_push: "Notifiche web push",
  },
};
