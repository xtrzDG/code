/** `bookingCalendar.*` in German: the bookings calendar (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { bookingCalendarEn } from "./bookingCalendar.en";

export const bookingCalendarDe: Translation<typeof bookingCalendarEn> = {
  views: {
    label: "Buchungen anzeigen als",
    list: "Liste",
    day: "Tag",
    week: "Woche",
    nights: "Nächte",
  },
  toolbar: {
    label: "Kalenderdaten",
    previous: { day: "Vorheriger Tag", week: "Vorherige Woche", nights: "Frühere Nächte" },
    next: { day: "Nächster Tag", week: "Nächste Woche", nights: "Spätere Nächte" },
    today: "Heute",
    date: "Datum",
    includeTest: "Testbuchungen zeigen",
  },
  loading: "Der Kalender wird geladen…",
  truncated:
    "In diesem Zeitraum gibt es mehr Buchungen, als der Kalender auf einmal zeigen kann. Öffnen Sie einen kürzeren Zeitraum oder die Liste.",
  legend: "Buchungsstatus",
  moveHint:
    "Ziehen Sie eine Buchung auf eine andere Zeit oder einen anderen Platz. Oder wählen Sie sie aus und nutzen Sie die Pfeiltasten: Enter verschiebt, Escape bricht ab.",
  day: {
    label: "Buchungen am {date} nach Platz",
    closed: "Geschlossen",
    closedDay: "Ganztägig geschlossen",
    newAt: "Neue Buchung: {place}",
    booked: "{percent} belegt",
    now: "Jetzt {time}",
    noPlacesTitle: "Keine Plätze, die nach Zeit gebucht werden",
    noPlacesDescription:
      "Fügen Sie Tische, Mitarbeitende oder Räume hinzu, die nach Zeit gebucht werden – der Tag zeigt dann jeden als eigene Spalte.",
    toPlaces: "Plätze hinzufügen",
  },
  block: {
    label: "{name}, {time}, {place}, {status}",
    test: "Test",
  },
  move: {
    pending: "Nach {place}, {time} verschieben? Enter verschiebt, Escape bricht ab.",
    pendingStay: "Nach {place} ab {date} verschieben? Enter verschiebt, Escape bricht ab.",
    moved: "Verschoben: {place}, {time}",
    movedStay: "Verschoben: {place} ab {date}",
    undone: "Die Buchung ist wieder an ihrem Platz",
    changed: "Jemand hat diese Buchung gerade geändert: Der Kalender zeigt sie jetzt so, wie sie ist.",
    cancelled: "Verschieben abgebrochen",
    tell: {
      title: "Neue Zeit an {name} mitteilen",
      titleAnonymous: "Neue Zeit dem Kunden mitteilen",
      hint: "Der Assistent schreibt Kunden nicht von selbst, wenn Sie eine Buchung im Kalender verschieben. Kopieren Sie den Text und senden Sie ihn im Kanal, in dem Sie schreiben.",
      show: "Nachricht anzeigen",
    },
  },
  week: {
    label: "Auslastung der Plätze, {range}",
    place: "Platz",
    allPlaces: "Alle Plätze",
    closed: "Geschlossen",
    free: "Frei",
    share: "{percent} belegt",
    rooms: { one: "{booked} von {open} Zimmer belegt", other: "{booked} von {open} Zimmern belegt" },
    cell: "{place}, {date}: {load}, {count}",
    legendTitle: "Auslastung",
    quiet: "Ruhig",
    full: "Voll",
  },
  nights: {
    label: "Zimmer nach Nacht, {range}",
    room: "Zimmer",
    taken: "{booked} von {open} belegt",
    newStay: "Neuer Aufenthalt: {place}, Nacht vom {date}",
    noRoomsTitle: "Keine Zimmer, die nach Nächten gebucht werden",
    noRoomsDescription:
      "Fügen Sie Zimmer oder Zimmerkategorien hinzu, die nach Nächten gebucht werden – jedes erscheint hier als eigene Zeile.",
  },
};
