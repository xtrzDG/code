/** `setupGuide.*` in German: the setup guide card and milestones (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { setupGuideEn } from "./setupGuide.en";

export const setupGuideDe: Translation<typeof setupGuideEn> = {
  titleSetup: "Richten Sie Ihren Assistenten ein",
  titleLive: "Gewinnen Sie die ersten Kunden",
  descriptionSetup: "Jeder Schritt öffnet sich dort, wo Sie aufgehört haben. Der Assistent antwortet Kunden, sobald er veröffentlicht ist.",
  liveSince: "Antwortet Kunden seit {date}",
  minutesLeft: { one: "noch etwa {count} Minute", other: "noch etwa {count} Minuten" },
  continueSetup: "Einrichtung fortsetzen",
  afterLaunchHint: "Nach dem Start: ein Test vom Handy, ein zweiter Kanal und der Link für Kunden.",
  minutes: "{count} Min.",
  optional: "optional",
  skip: "Überspringen",
  unskip: "Zurückholen",
  skipLabel: "„{step}“ überspringen",
  unskipLabel: "„{step}“ zurückholen",
  status: {
    next: "Als Nächstes",
    skipped: "Übersprungen",
  },
  phone: {
    description: "Richten Sie die Handykamera auf den Code und schreiben Sie dem Assistenten wie ein Kunde.",
    qrAlt: "QR-Code von {link}",
    copyLink: "Link kopieren",
    unavailable: "Die Chat-Seite ist aus. Schalten Sie den Website-Chat unter Kanäle ein oder schreiben Sie vom Handy an einen verbundenen Messenger.",
    orTelegram: "Oder in Telegram:",
    listening: "Warten auf Ihre Nachricht…",
    hint: "Der Schritt ist erledigt, wenn Ihre Nachricht ankommt.",
    success: "Es funktioniert: Ihre Nachricht hat den Assistenten erreicht.",
    hide: "Ausblenden",
  },
  finished: {
    title: "Alles erledigt",
    description: "Der Assistent antwortet Kunden, und sie wissen, wo sie ihn finden.",
    dismiss: "Diese Karte ausblenden",
  },
  wins: {
    title: "Erreicht",
    first_conversation: "Erstes Kundengespräch",
    first_booking: "Erste Buchung",
    first_after_hours_booking: "Erste Buchung außerhalb der Zeiten",
  },
  ring: {
    title: "Einrichtung",
    label: "Einrichtung zu {percent} % erledigt",
    short: "{percent} %",
  },
  celebrations: {
    first_conversation: {
      title: "Der erste Kunde hat geschrieben",
      description: "Der Assistent hat geantwortet. Das Gespräch ist im Posteingang.",
    },
    first_booking: {
      title: "Die erste Buchung",
      description: "Der Assistent hat einen Kunden selbst gebucht.",
    },
    first_after_hours_booking: {
      title: "Eine Buchung, während Sie geschlossen hatten",
      description: "Ein Kunde hat außerhalb der Zeiten gebucht, und niemand musste rangehen.",
    },
    openInbox: "Posteingang öffnen",
    openBookings: "Buchungen öffnen",
    close: "Schließen",
  },
};
