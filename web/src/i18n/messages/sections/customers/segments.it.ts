/** `segments.*` in Italian: Customers → Segments (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { segmentsEn } from "./segments.en";

export const segmentsIt: Translation<typeof segmentsEn> = {
  loading: "Caricamento dei segmenti…",
  new: "Nuovo segmento",
  empty: "Ancora nessun segmento",
  emptyDescription: "Salva un gruppo di clienti, per esempio gli abituali che non tornano da 60 giorni, e scaricalo per una campagna.",
  limit: "Un'attività può avere al massimo 50 segmenti. Eliminane uno per salvarne un altro.",
  members: "Clienti",
  noMembers: "Al momento nessuno corrisponde a questo segmento.",
  export: "Scarica CSV",
  exportHint: "I clienti del segmento con telefoni, canali, tag e prenotazioni, per una campagna su un altro strumento.",
  edit: "Modifica",
  delete: "Elimina",
  deleteTitle: "Eliminare il segmento “{name}”?",
  deleteBody: "Vengono eliminate solo le regole salvate; nessun cliente viene modificato.",
  deleted: "Segmento eliminato",
  saved: "Segmento salvato",
  editor: {
    newTitle: "Nuovo segmento",
    editTitle: "Modifica il segmento",
    name: "Nome",
    namePlaceholder: "es. Non tornati da 60 giorni",
    rules: "Chi ne fa parte",
    rulesHint: "Ogni regola compilata deve essere rispettata. I clienti bloccati o con dati cancellati non ne fanno mai parte.",
    tag: "Tag",
    anyTag: "Qualsiasi tag",
    lastVisit: "Ultima visita più di … giorni fa",
    minBookings: "Almeno … prenotazioni",
    maxBookings: "Al massimo … prenotazioni",
    vipOnly: "Solo clienti VIP",
    save: "Salva il segmento",
  },
  errors: {
    name: "Dai un nome al segmento (fino a 60 caratteri).",
    days: "I giorni devono essere un numero intero da 1 a 3650.",
    bookings: "Le prenotazioni devono essere un numero intero da 0 a 10000.",
    minMax: "“Almeno” non può essere maggiore di “al massimo”.",
  },
  preview: {
    counting: "Conteggio…",
    count: { one: "{count} cliente corrisponde", other: "{count} clienti corrispondono" },
    atLeast: { one: "Almeno {count} cliente corrisponde", other: "Almeno {count} clienti corrispondono" },
    none: "Ancora nessuno corrisponde.",
  },
  summary: {
    everyone: "Tutti i clienti",
    tag: "tag “{tag}”",
    lastVisit: { one: "ultima visita più di {count} giorno fa", other: "ultima visita più di {count} giorni fa" },
    minBookings: { one: "almeno {count} prenotazione", other: "almeno {count} prenotazioni" },
    maxBookings: { one: "al massimo {count} prenotazione", other: "al massimo {count} prenotazioni" },
    vipOnly: "solo VIP",
  },
};
