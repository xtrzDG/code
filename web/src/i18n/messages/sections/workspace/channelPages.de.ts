/** `channelPages.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { channelPagesEn } from "./channelPages.en";

export const channelPagesDe: Translation<typeof channelPagesEn> = {
  heading: "Einrichten",
  back: "Alle Kanäle",
  website: {
    title: "Website-Chat",
    hint: "Farbe, Schaltfläche, der Code für Ihre Website und wo er erscheinen darf",
  },
  calls: {
    title: "Anrufweiterleitung",
    hint: "Codes, die verpasste Anrufe an den Assistenten weiterleiten",
  },
  share: {
    title: "Teilen",
    hint: "Links, ein QR-Code und ein Tischaufsteller",
  },
  off: {
    website: "Der Website-Chat ist aus. Schalten Sie ihn unter den Kanälen ein, um sein Aussehen zu wählen und ihn auf Ihre Website zu setzen.",
    calls: "Der Telefonkanal ist nicht verbunden. Verbinden Sie ihn unter den Kanälen, um Ihre Weiterleitungscodes zu bekommen.",
  },
};
