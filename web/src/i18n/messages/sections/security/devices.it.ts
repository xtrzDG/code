/** `devices.*` texts of Account → Security, signed-in devices, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { devicesEn } from "./devices.en";

export const devicesIt: Translation<typeof devicesEn> = {
  title: "Dove hai effettuato l'accesso",
  description:
    "Tutti i browser e i telefoni collegati al tuo account. Una sessione che nessuno usa per 7 giorni termina da sola.",
  descriptionAdmin:
    "Tutti i browser e i telefoni collegati al tuo account. Come amministratore della piattaforma, una sessione termina dopo 12 ore di inattività e un giorno dopo l'accesso.",
  thisDevice: "Questo dispositivo",
  kind: {
    desktop: "Computer",
    phone: "Telefono",
    tablet: "Tablet",
    unknown: "Dispositivo",
  },
  on: "{browser} su {system}",
  signedIn: "Accesso: {date}",
  lastUsed: "Ultimo utilizzo: {date}",
  from: "da {address}",
  fromCountry: "da {address} ({country})",
  twoFactor: "Con un secondo fattore",
  oneFactor: "Con un codice di accesso",
  ends: "Scade: {date}",
  end: "Disconnetti",
  endLabel: "Disconnetti {device}",
  endTitle: "Disconnettere questo dispositivo?",
  endDescription: "Chi lo usa dovrà accedere di nuovo.",
  ended: "Il dispositivo è stato disconnesso",
  endOthers: "Disconnetti tutti gli altri",
  endOthersTitle: "Disconnettere tutti gli altri dispositivi?",
  endOthersDescription:
    "Tutti i browser e i telefoni tranne questo dovranno accedere di nuovo.",
  endedOthers: {
    one: "{count} dispositivo disconnesso",
    other: "{count} dispositivi disconnessi",
  },
  onlyThis: "L'accesso è attivo solo su questo dispositivo.",
  notYou:
    "Non riconosci un dispositivo? Disconnettilo, poi attiva l'app di autenticazione qui sopra.",
};
