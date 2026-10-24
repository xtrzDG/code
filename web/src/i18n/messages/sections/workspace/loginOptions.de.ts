/** `loginOptions.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { loginOptionsEn } from "./loginOptions.en";

export const loginOptionsDe: Translation<typeof loginOptionsEn> = {
  channelLabel: "Code senden per",
  noPhoneChannels: "An Telefonnummern dieses Landes können gerade keine Anmeldecodes gesendet werden.",
  useEmail: "Mit E-Mail anmelden",
  nothingAvailable: "Die Anmeldung ist vorübergehend nicht verfügbar: Es gibt noch keinen Weg, Anmeldecodes zuzustellen. Bitte versuchen Sie es später erneut.",
  restricted: "Die Registrierung ist in diesem Land noch nicht verfügbar.",
};
