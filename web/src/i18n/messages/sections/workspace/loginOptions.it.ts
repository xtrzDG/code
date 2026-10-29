/** `loginOptions.*` texts of the sign-in code channels, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { loginOptionsEn } from "./loginOptions.en";

export const loginOptionsIt: Translation<typeof loginOptionsEn> = {
  channelLabel: "Invia il codice tramite",
  noPhoneChannels: "Al momento non è possibile inviare codici di accesso ai numeri di telefono di questo paese.",
  useEmail: "Accedi con l'e-mail",
  nothingAvailable: "L'accesso non è temporaneamente disponibile: non c'è ancora un modo per inviare i codici di accesso. Riprova più tardi.",
  restricted: "La registrazione non è ancora disponibile in questo paese.",
};
