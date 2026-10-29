/** `bookingCalendar.*` in Italian: the bookings calendar (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { bookingCalendarEn } from "./bookingCalendar.en";

export const bookingCalendarIt: Translation<typeof bookingCalendarEn> = {
  views: {
    label: "Mostra le prenotazioni come",
    list: "Elenco",
    day: "Giorno",
    week: "Settimana",
    nights: "Notti",
  },
  toolbar: {
    label: "Date del calendario",
    previous: { day: "Giorno precedente", week: "Settimana precedente", nights: "Notti precedenti" },
    next: { day: "Giorno successivo", week: "Settimana successiva", nights: "Notti successive" },
    today: "Oggi",
    date: "Data",
    includeTest: "Mostra le prenotazioni di prova",
  },
  loading: "Caricamento del calendario…",
  truncated: "In questo periodo ci sono più prenotazioni di quante il calendario possa mostrarne insieme. Apri un periodo più breve, oppure l'elenco.",
  legend: "Stato della prenotazione",
  moveHint: "Trascina una prenotazione su un altro orario o posto. Oppure selezionala e usa i tasti freccia: Invio la sposta, Esc annulla.",
  day: {
    label: "Prenotazioni per posto, {date}",
    closed: "Chiuso",
    closedDay: "Chiuso tutto il giorno",
    newAt: "Nuova prenotazione: {place}",
    booked: "{percent} prenotato",
    now: "Ora {time}",
    noPlacesTitle: "Nessun posto prenotabile a orario",
    noPlacesDescription: "Aggiungi i tavoli, i professionisti o le sale che gli ospiti prenotano a orario: nella vista giorno ognuno avrà la sua colonna.",
    toPlaces: "Aggiungi posti",
  },
  block: {
    label: "{shown}, {place}, {status}",
    until: "fino alle {time}",
    test: "Test",
  },
  move: {
    pending: "Spostare su {place} alle {time}? Invio la sposta, Esc annulla.",
    pendingStay: "Spostare su {place} dal {date}? Invio la sposta, Esc annulla.",
    moved: "Spostata su {place} alle {time}",
    movedStay: "Spostata su {place} dal {date}",
    undone: "La prenotazione è tornata dov'era",
    changed: "Qualcuno ha modificato questa prenotazione poco fa: ora il calendario la mostra aggiornata.",
    cancelled: "Spostamento annullato",
    tell: {
      title: "Comunica a {name} il nuovo orario",
      titleAnonymous: "Comunica al cliente il nuovo orario",
      hint: "L'assistente non avvisa i clienti degli spostamenti fatti nel calendario. Copia il testo e invialo nel canale in cui vi sentite.",
      show: "Mostra il messaggio",
    },
  },
  week: {
    label: "Occupazione di ogni posto, {range}",
    place: "Posto",
    allPlaces: "Tutti i posti",
    closed: "Chiuso",
    free: "Libero",
    share: "{percent} prenotato",
    rooms: { one: "{booked} su {open} camera occupata", other: "{booked} su {open} camere occupate" },
    cell: "{place}, {date}: {load}, {count}",
    legendTitle: "Occupazione",
    quiet: "Bassa",
    full: "Al completo",
  },
  nights: {
    label: "Camere per notte, {range}",
    room: "Camera",
    taken: "{booked} su {open} occupate",
    newStay: "Nuovo soggiorno: {place}, notte del {date}",
    noRoomsTitle: "Nessuna camera prenotabile a notte",
    noRoomsDescription: "Aggiungi le camere o le tipologie di camera che gli ospiti prenotano a notte: qui ognuna avrà la sua riga.",
  },
};
