/** `setup.*` in German: creating the assistant before it exists (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { setupEn } from "./setup.en";

export const setupDe: Translation<typeof setupEn> = {
  navEntry: "KI-Assistenten erstellen",
  navEntryHint: "Schritt für Schritt, etwa 20 Minuten",
  eyebrow: "{business}",
  title: "Erstellen wir Ihren KI-Assistenten",
  description:
    "Erzählen Sie uns in wenigen einfachen Schritten von Ihrem Unternehmen. Wir bereiten einen Assistenten vor, der Ihren Kunden Tag und Nacht antwortet, Buchungen annimmt und Sie ruft, wenn eine Person gebraucht wird.",
  start: "KI-Assistenten erstellen",
  continue: "Weiter erstellen",
  progress: { one: "{done} von {total} Schritt erledigt", other: "{done} von {total} Schritten erledigt" },
  duration: "Etwa 20 Minuten. Sie können jederzeit pausieren und später weitermachen.",
  stagesLabel: "So läuft es ab",
  stages: {
    business: {
      title: "Erzählen Sie von Ihrem Unternehmen",
      description: "Kontakte, Öffnungszeiten und was Sie anbieten.",
    },
    rules: {
      title: "Bringen Sie ihm Ihre Regeln bei",
      description: "Buchungen, Antworten auf häufige Fragen und wann Sie gerufen werden.",
    },
    meet: {
      title: "Lernen Sie Ihren Assistenten kennen",
      description: "Testen Sie ihn im Chat und schalten Sie ihn dann für Ihre Kunden ein.",
    },
  },
  staffTitle: "Der Assistent wird gerade erstellt",
  staffDescription:
    "Der Inhaber von {business} richtet ihn ein. Gespräche, Buchungen und Anfragen erscheinen hier, sobald er bereit ist.",
  create: "Meinen Assistenten erstellen",
};
