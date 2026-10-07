/** `account.*` in German: the user menu (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { accountEn } from "./account.en";

export const accountDe: Translation<typeof accountEn> = {
  menu: "Konto und Einstellungen",
  signedInAs: "Angemeldet als",
  preferences: "Einstellungen",
  businesses: "Alle Unternehmen",
  admin: "Plattform-Verwaltung",
  install: "App installieren",
  installHint: "Öffnen Sie das Dashboard wie eine App über den Startbildschirm oder das Dock.",
  installIosTitle: "App auf iPhone oder iPad installieren",
  installIosSteps: "Tippen Sie in Safari unten auf „Teilen“ und dann auf „Zum Home-Bildschirm“.",
};
