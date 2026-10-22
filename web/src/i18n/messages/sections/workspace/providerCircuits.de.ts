/** `providerCircuits.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { providerCircuitsEn } from "./providerCircuits.en";

export const providerCircuitsDe: Translation<typeof providerCircuitsEn> = {
  title: "Schutzschalter der Anbieter",
  description:
    "Jeder Anbieter, über den die Worker senden, hat einen Schutzschalter. Fünf Fehler in einer Minute öffnen ihn: Nachrichten warten ohne Aufruf, und 30 s später geht ein Probeversand durch. Ein Anbieter belegt höchstens die Hälfte der Zustell-Threads eines Workers.",
  none: "Kein Worker hat seine Schutzschalter gemeldet",
  noneDescription: "Worker melden ihre Schutzschalter mit jedem Lebenszeichen; ein Worker eines älteren Releases meldet keine.",
  circuit: "Schutzschalter",
  state: "Zustand",
  workers: "Worker, in denen er nicht geschlossen ist",
  workersOf: "{notClosed} von {total}",
  failures: "Fehler in der letzten Minute",
  opened: "Geöffnet",
  states: {
    closed: "Geschlossen",
    half_open: "Probeversand",
    open: "Offen",
  },
  providers: {
    meta: "Meta (WhatsApp, Messenger, Instagram)",
    telegram: "Telegram-Bots",
    platform_bot: "Plattform-Bot",
    twilio_sms: "SMS (Twilio)",
    smtp: "E-Mail (SMTP)",
    flitt: "Zahlungen (Flitt)",
    web_push: "Web-Push",
  },
};
