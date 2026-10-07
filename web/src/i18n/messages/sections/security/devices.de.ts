/** `devices.*` in German: Account → Security, signed-in devices (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { devicesEn } from "./devices.en";

export const devicesDe: Translation<typeof devicesEn> = {
  title: "Wo Sie angemeldet sind",
  description: "Jeder Browser und jedes Telefon, das bei Ihrem Konto angemeldet ist. Eine Sitzung, die 7 Tage niemand nutzt, endet von selbst.",
  descriptionAdmin:
    "Jeder Browser und jedes Telefon, das bei Ihrem Konto angemeldet ist. Als Plattform-Admin endet eine Sitzung nach 12 Stunden ohne Nutzung und einen Tag nach der Anmeldung.",
  thisDevice: "Dieses Gerät",
  kind: {
    desktop: "Computer",
    phone: "Telefon",
    tablet: "Tablet",
    unknown: "Gerät",
  },
  on: "{browser} auf {system}",
  signedIn: "Angemeldet {date}",
  lastUsed: "Zuletzt genutzt {date}",
  from: "von {address}",
  twoFactor: "Mit der Authenticator-App",
  oneFactor: "Mit einem Anmeldecode",
  ends: "Endet von selbst {date}",
  end: "Abmelden",
  endLabel: "{device} abmelden",
  endTitle: "Dieses Gerät abmelden?",
  endDescription: "Wer es nutzt, muss sich erneut anmelden.",
  ended: "Das Gerät ist abgemeldet",
  endOthers: "Überall sonst abmelden",
  endOthersTitle: "Alle anderen Geräte abmelden?",
  endOthersDescription: "Jeder Browser und jedes Telefon außer diesem muss sich erneut anmelden.",
  endedOthers: {
    one: "{count} Gerät abgemeldet",
    other: "{count} Geräte abgemeldet",
  },
  onlyThis: "Nur dieses Gerät ist angemeldet.",
  notYou: "Erkennen Sie ein Gerät nicht? Melden Sie es ab und schalten Sie dann oben die Authenticator-App ein.",
};
