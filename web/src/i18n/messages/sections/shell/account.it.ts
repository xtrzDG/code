/** `account.*` texts of the user menu, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { accountEn } from "./account.en";

export const accountIt: Translation<typeof accountEn> = {
  menu: "Account e preferenze",
  signedInAs: "Accesso effettuato come",
  preferences: "Preferenze",
  businesses: "Tutte le attività",
  admin: "Amministrazione della piattaforma",
  install: "Installa l'app",
  installHint: "Apri il pannello dalla schermata Home o dal Dock, come un'app.",
  installIosTitle: "Installa l'app su iPhone o iPad",
  installIosSteps: "In Safari, tocca Condividi in fondo allo schermo, poi “Aggiungi alla schermata Home”.",
  motion: "Riduci il movimento",
  motionHint: "Mantiene il pannello fermo su questo dispositivo: niente animazioni, numeri che scorrono o effetti 3D. L'impostazione del dispositivo viene sempre rispettata.",
};
