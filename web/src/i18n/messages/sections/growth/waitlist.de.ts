/** `waitlist.*` in German: Bookings → Waitlist (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { waitlistEn } from "./waitlist.en";

export const waitlistDe: Translation<typeof waitlistEn> = {
  loading: "Die Warteliste wird geladen…",
  filters: {
    label: "Welche Einträge",
    active: "Wartend",
    booked: "Gebucht",
    ended: "Beendet",
  },
  empty: {
    active: "Niemand wartet",
    activeDescription:
      "Wenn ein Tag ausgebucht ist, bietet der Assistent dem Kunden die Warteliste an. Ein durch Absage oder Verschiebung frei gewordener Platz wird dem Ersten angeboten, zu dem er passt.",
    booked: "Noch keine Buchungen von der Warteliste",
    bookedDescription: "Kunden, die einen frei gewordenen Platz angenommen haben, erscheinen hier mit ihrer Buchung.",
    ended: "Noch nichts beendet",
    endedDescription: "Einträge enden, wenn der Kunde ablehnt, nicht rechtzeitig antwortet oder der Tag vorbei ist.",
  },
  customer: "Kunde",
  wants: "Möchte {date}",
  window: {
    any: "jederzeit",
    between: "{from}–{to}",
    from: "ab {from}",
    until: "bis {to}",
  },
  nights: { one: "{count} Nacht", other: "{count} Nächte" },
  status: {
    waiting: "Wartet",
    offered: "Platz reserviert",
    booked: "Gebucht",
    expired: "Beendet",
  },
  endReasons: {
    declined: "Hat den Platz abgelehnt",
    no_answer: "Hat nicht rechtzeitig geantwortet",
    date_passed: "Der Tag ist vorbei",
    unreachable: "War nicht erreichbar",
    removed: "Von der Liste genommen",
  },
  offer: {
    held: "Für den Kunden reserviert: {place}, {time}",
    heldNoPlace: "Für den Kunden reserviert: {time}",
    until: "Bis {time}",
    minutesLeft: { one: "Noch {count} Minute", other: "Noch {count} Minuten" },
    answerDue: "Wartet auf Antwort",
  },
  offerCount: { one: "{count}-mal ein Platz angeboten", other: "{count}-mal ein Platz angeboten" },
  joined: "Eingetragen {time}",
  booked: "Gebucht {time}",
  ended: "Beendet {time}",
  openConversation: "Gespräch öffnen",
  remove: "Von der Liste nehmen",
  removeTitle: "{name} von der Warteliste nehmen?",
  removeBody: "Dem Kunden wird kein frei gewordener Platz mehr angeboten. Ein gerade reservierter Platz geht an den Nächsten in der Reihe.",
  removeConfirm: "Von der Liste nehmen",
  removed: "Von der Warteliste genommen",
  timeZone: "Uhrzeiten in {timezone}.",
  settings: {
    title: "Einstellungen der Warteliste",
    description:
      "Eine abgesagte oder verschobene Buchung macht einen Platz frei: Er wird für den ersten passenden Kunden reserviert und ihm in seinem Kanal und seiner Sprache angeboten. Ein „Ja“ bucht ihn.",
    toggle: "Warteliste führen",
    off: "Der Assistent bietet die Warteliste nicht an. Kunden, die schon darauf stehen, bleiben bis zu ihrem Tag.",
    hold: "Einen frei gewordenen Platz reservieren für",
    holdHint: "Ohne Antwort bis dahin geht der Platz an den Nächsten in der Reihe.",
    holdOption: { one: "{count} Minute", other: "{count} Minuten" },
    save: "Speichern",
    saved: "Die Einstellungen der Warteliste sind gespeichert",
    ownersOnly: "Nur ein Inhaber kann diese Einstellungen ändern.",
  },
};
