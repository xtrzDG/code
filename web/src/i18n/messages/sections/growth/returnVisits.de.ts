/** `returnVisits.*` in German: Bookings → Return visits (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { returnVisitsEn } from "./returnVisits.en";

export const returnVisitsDe: Translation<typeof returnVisitsEn> = {
  loading: "Wiederkehrende Besuche werden geladen…",
  rules: {
    rebook: "Eine Einladung zurückzukommen",
    recall: "Eine Erinnerung, dass eine Kontrolle fällig ist",
    pre_arrival: "Eine Nachricht vor der Anreise",
  },
  ruleHints: {
    rebook: "Wird die gewählte Anzahl Tage nach dem letzten Besuch gesendet, es sei denn, der Kunde hat schon wieder gebucht.",
    recall: "Wird die gewählte Anzahl Tage nach dem letzten Besuch gesendet, für eine regelmäßige Kontrolle oder einen Service.",
    pre_arrival: "Wird die gewählte Anzahl Tage vor Beginn einer Buchung gesendet, mit einer Erinnerung an das Datum.",
  },
  settings: {
    title: "Wiederkehr-Nachrichten",
    description: "Eine Nachricht, die Kunden zurückbringt, in ihrem Kanal und ihrer Sprache. Nichts wird gesendet, bevor Sie es einschalten.",
    toggle: "Wiederkehr-Nachrichten senden",
    rule: "Was gesendet wird",
    daysAfter: "Tage nach dem letzten Besuch",
    daysBefore: "Tage vor der Anreise",
    suggested: {
      one: "Üblich für Ihre Branche: „{rule}“ nach {count} Tag.",
      other: "Üblich für Ihre Branche: „{rule}“ nach {count} Tagen.",
    },
    suggestedBefore: {
      one: "Üblich für Ihre Branche: „{rule}“ {count} Tag vorher.",
      other: "Üblich für Ihre Branche: „{rule}“ {count} Tage vorher.",
    },
    useSuggested: "Übernehmen",
    audience: "Wer sie bekommen darf",
    audiences: {
      all_customers: "Jeder Kunde, den die Regel findet",
      segment: "Nur die Kunden eines Segments",
    },
    segment: "Segment",
    chooseSegment: "Segment wählen",
    noSegments: "Es gibt noch keine gespeicherten Segmente.",
    toSegments: "Legen Sie eines unter Kunden → Segmente an",
    cap: "Höchstens pro Monat",
    capHint: "Bei dieser Anzahl stoppen die Nachrichten für den Rest des Monats.",
    monthSent: {
      one: "{count} Nachricht in diesem Monat gesendet, von {cap}",
      other: "{count} Nachrichten in diesem Monat gesendet, von {cap}",
    },
    honours:
      "Kunden, die STOP geschrieben haben, auf der Sperrliste stehen oder blockiert sind, bekommen sie nie. Ein Kunde bekommt höchstens alle zwei Wochen eine solche Nachricht und keine mehr, nachdem er wieder gebucht hat.",
    whatsapp:
      "Auf WhatsApp bekommt ein Kunde, der seit 24 Stunden nicht geschrieben hat, die genehmigte Vorlage der Plattform für Einladungen und Erinnerungen; eine Nachricht vor der Anreise wartet auf ein offenes Gespräch.",
    save: "Speichern",
    saved: "Die Wiederkehr-Nachrichten sind gespeichert",
    errors: {
      days: "Die Tage sind eine ganze Zahl von 1 bis 730.",
      cap: "Die Monatsgrenze ist eine ganze Zahl von 1 bis 2000.",
      segment: "Wählen Sie ein Segment oder schreiben Sie jedem Kunden, den die Regel findet.",
    },
  },
  recent: {
    title: "Die letzten 30 Tage",
    sent: "Gesendet",
    booked: "Wieder gebucht",
    skipped: "Nicht gesendet",
  },
  preview: {
    title: "Was Kunden lesen",
    description: "Die Nachricht in jeder Sprache Ihres Unternehmens, mit dem Datum, wie es heute eingesetzt würde.",
  },
  messages: {
    title: "Neueste Nachrichten",
    description: "Wer eine Nachricht bekommen hat und wer danach wieder gebucht hat.",
    empty: "Noch keine Nachrichten",
    emptyDescription: "Wenn die Nachrichten eingeschaltet sind, schreibt eine stündliche Prüfung den fälligen Kunden.",
    customer: "Kunde",
    status: {
      sent: "Gesendet",
      booked: "Wieder gebucht",
      skipped: "Nicht gesendet",
    },
    skipReasons: {
      opted_out: "der Kunde möchte nicht angeschrieben werden",
      no_contact: "der Kunde ist unbekannt oder gelöscht",
      no_channel: "es gibt keinen Kanal, um ihn zu erreichen",
      window_closed: "das 24-Stunden-Fenster ist geschlossen und es gibt keine Vorlage",
    },
    notSentBecause: "Nicht gesendet: {reason}",
    sentAt: "Gesendet {time}",
    bookedAt: "Gebucht {time}",
    openConversation: "Gespräch öffnen",
    showMore: "Mehr anzeigen",
  },
};
