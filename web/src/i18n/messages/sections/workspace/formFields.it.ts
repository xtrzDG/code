/** `formFields.*` texts of the UI kit's date and time fields and of self-saving settings forms, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { formFieldsEn } from "./formFields.en";

export const formFieldsIt: Translation<typeof formFieldsEn> = {
  time: {
    hours: "Ore",
    minutes: "Minuti",
    dayPeriod: "AM o PM",
    empty: "Non impostato",
  },
  date: {
    placeholder: "Scegli una data",
    open: "Apri il calendario",
    calendar: "Calendario",
    previousMonth: "Mese precedente",
    nextMonth: "Mese successivo",
    today: "Oggi",
    clear: "Cancella",
    date: "Data",
    time: "Ora",
  },
  autosave: {
    hint: "Le modifiche si salvano da sole.",
    saving: "Salvataggio…",
    saved: "Salvato",
    failed: "Non salvato",
    retry: "Riprova",
  },
};
