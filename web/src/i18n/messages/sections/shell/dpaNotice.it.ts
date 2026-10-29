/** `dpaNotice.*` texts of the new data processing agreement banner, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { dpaNoticeEn } from "./dpaNotice.en";

export const dpaNoticeIt: Translation<typeof dpaNoticeEn> = {
  label: "Nuovo accordo sul trattamento dei dati",
  title: "È disponibile una nuova versione ({version}) dell'accordo sul trattamento dei dati",
  due: "Sostituisce la versione che hai accettato. Leggila e accettala entro il {date}: per applicare modifiche all'assistente serve la versione in vigore.",
  overdue:
    "Sostituisce la versione che hai accettato e andava accettata entro il {date}: per applicare modifiche all'assistente serve la versione in vigore, quindi leggila e accettala ora.",
  action: "Leggi e accetta",
};
