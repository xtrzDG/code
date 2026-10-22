/** `securityNudge.*` texts in German: the owner's second-factor banner. */

import type { Translation } from "../../../translate";
import type { securityNudgeEn } from "./securityNudge.en";

export const securityNudgeDe: Translation<typeof securityNudgeEn> = {
  title: "Schützen Sie die Daten Ihrer Kunden: Schalten Sie einen zweiten Faktor ein",
  description:
    "Mit einem Passkey oder einer Authenticator-App öffnet ein gestohlener Anmeldecode allein Ihr Dashboard nicht.",
  teamGrew:
    "Ihr Team ist gewachsen: Mehr Menschen sehen die Daten Ihrer Kunden. Schalten Sie einen zweiten Faktor ein.",
  action: "Einschalten",
  dismiss: "Nicht jetzt",
};
