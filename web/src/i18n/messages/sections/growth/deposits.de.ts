/** `deposits.*` auf Deutsch: die Anzahlung, die eine Buchung bis zur Zahlung auf der Seite des Inhabers hält. */

import type { Translation } from "../../../translate";
import type { depositsEn } from "./deposits.en";

export const depositsDe: Translation<typeof depositsEn> = {
  chip: "Anzahlung",
  status: {
    awaiting: "Wartet auf Zahlung",
    paid: "Bezahlt",
    expired: "Nicht rechtzeitig bezahlt",
    cancelled: "Storniert",
    refund_due: "Zu erstatten",
    kept: "Einbehalten",
  },
  booking: {
    label: "Anzahlung",
    heldUntil: "Der Platz ist bis {time} reserviert",
    reference: "Zahlungscode: {reference}",
    markPaid: "Bezahlt",
    confirmTitle: "Anzahlung als bezahlt markieren?",
    confirmDescription:
      "Tun Sie das, sobald Sie {amount} mit dem Code {reference} in Ihrem Händlerkonto sehen. Die Buchung wird dann bestätigt.",
    confirm: "Ja, bezahlt",
    marked: "Anzahlung als bezahlt markiert",
    refundDue: "Die Buchung wurde rechtzeitig storniert: Erstatten Sie die Anzahlung über Ihr Händlerkonto.",
  },
  policy: {
    title: "Anzahlung",
    description:
      "Wird beim Buchen auf Ihrer Zahlungsseite bezahlt. Der Betrag kommt immer von hier, nie vom Assistenten.",
    rule: "Anzahlung",
    rules: {
      none: "Keine Anzahlung",
      fixed: "Fester Betrag pro Buchung",
      per_guest: "Betrag pro Gast",
      percent_of_value: "Prozent des Buchungswerts",
    },
    amount: "Betrag, {currency}",
    amountPerGuest: "Betrag pro Gast, {currency}",
    percent: "Prozent des Werts",
    minParty: "Ab wie vielen Gästen",
    minPartyHint: "Leer lassen, um bei jeder Buchung zu fragen.",
    page: "Zahlungsseite",
    defaultPage: "Die Standardseite",
    pageHint: "Eine Seite mit einem festen Betrag passt nur zu einer festen Anzahlung in genau dieser Höhe.",
    save: "Anzahlung speichern",
    saved: "Anzahlung gespeichert",
    removed: "Es wird jetzt keine Anzahlung verlangt",
    off: "Anzahlungen sind ausgeschaltet, daher wird noch niemand gefragt.",
    noPage: "Fügen Sie zuerst Ihre Zahlungsseite hinzu.",
    openSettings: "Einstellungen für Anzahlungen",
    summary: {
      fixed: "Anzahlung {amount}",
      per_guest: "Anzahlung {amount} pro Gast",
      percent_of_value: "Anzahlung {percent} % des Werts",
    },
    fromGuests: { one: "ab {count} Gast", other: "ab {count} Gästen" },
    errors: {
      percent: "Geben Sie einen Prozentwert von 1 bis 100 ein.",
      minParty: "Geben Sie eine ganze Zahl an Gästen ein, mindestens 1.",
    },
  },
  settings: {
    title: "Anzahlungen",
    description:
      "Halten Sie eine Buchung, bis der Kunde eine Anzahlung auf Ihrer eigenen Zahlungsseite leistet. Der Assistent sendet Ihren Link mit dem Betrag, den Sie festlegen; Betrag oder Link wählt er nie selbst.",
    toggle: "Anzahlungen verlangen",
    toggleHint: "Tische, Zimmer, Mitarbeitende und Leistungen mit Anzahlung verlangen sie beim Buchen.",
    turnedOff: "Anzahlungen ausgeschaltet",
    holdMinutes: "Auf die Zahlung warten, Minuten",
    holdHint:
      "Von 15 Minuten bis zu einem Tag. Bei 30 Minuten oder mehr erhält der Kunde zur Hälfte eine Erinnerung; ein unbezahlter Platz wird danach freigegeben und der Kunde benachrichtigt.",
    refundHours: "Erstattung bei Storno, Stunden vor dem Besuch",
    refundHint: "Früher storniert: Sie erstatten die Anzahlung. Später oder nicht erschienen: Die Anzahlung bleibt bei Ihnen.",
    manual:
      "Zahlungen bestätigen Sie selbst: Sobald das Geld in Ihrem Händlerkonto ist, öffnen Sie die Buchung und tippen auf „Bezahlt“. Eine automatische Bestätigung durch den Zahlungsanbieter ist nicht angebunden.",
    errors: {
      hold: "Geben Sie 15 bis 1440 Minuten ein.",
      refund: "Geben Sie 0 bis 720 Stunden ein.",
    },
  },
  pages: {
    title: "Zahlungsseiten",
    description:
      "Ihre eigenen Seiten, auf denen Kunden bezahlen: Flitt, Stripe Payment Links, TBC, Bank of Georgia oder jeder Anbieter mit einem Link, in jedem Land und jeder Währung.",
    empty: "Noch keine Zahlungsseite",
    emptyDescription: "Fügen Sie den Link Ihrer Zahlungsseite hinzu. Der Assistent sendet ihn mit der Anzahlung.",
    add: "Seite hinzufügen",
    label: "Name",
    labelPlaceholder: "Flitt, Anzahlungen für Tische",
    kind: "Art",
    kinds: {
      template: "Setzt den Betrag ein",
      static: "Ein fester Betrag",
    },
    kindHints: {
      template: "Setzen Sie {amount} dort ein, wo der Betrag steht, und {reference} dort, wo der Zahlungscode steht.",
      static: "Eine Seite, die immer denselben Betrag abbucht: Sie passt nur zu einer festen Anzahlung.",
    },
    address: "Link",
    addressHint: "Nur https. Ein Link mit Schlüssel wird verschlüsselt gespeichert und ohne ihn angezeigt.",
    sealed: "Schlüssel verborgen",
    default: "Standard",
    makeDefault: "Als Standard festlegen",
    defaultHint: "Die Seite, die Anzahlungen nutzen, wenn ein Tisch, Zimmer, Mitarbeiter oder eine Leistung keine andere nennt.",
    removeLabel: "{label} entfernen",
    removeTitle: "Diese Zahlungsseite entfernen?",
    removeDescription:
      "Bereits verlangte Anzahlungen behalten ihren Link. Anzahlungen, die auf diese Seite eingestellt sind, nutzen die Standardseite.",
    added: "Zahlungsseite hinzugefügt",
    removed: "Zahlungsseite entfernt",
    defaultSet: "Standardseite geändert",
    errors: {
      label: "Geben Sie einen Namen ein.",
      address: "Geben Sie den Link ein.",
    },
    refusals: {
      linkNotHttps: "Der Link muss mit https:// beginnen.",
      linkInvalid: "Dieser Link kann nicht verwendet werden: Prüfen Sie die Adresse.",
      templateInvalid:
        "Eine Seite, die den Betrag einsetzt, braucht {amount} im Link, und nur {amount}, {amount_minor}, {currency} und {reference} werden eingesetzt.",
      noPaymentLink: "Wählen Sie eine Ihrer Zahlungsseiten, die den Betrag einsetzt.",
      depositsOff: "Anzahlungen sind ausgeschaltet.",
      currencyMismatch: "Die Anzahlung muss in der Währung des Unternehmens sein.",
      statusChanged: "Diese Anzahlung hat sich inzwischen geändert: Sie wartet nicht mehr auf eine Zahlung.",
    },
  },
  banquet: {
    title: "Bankettanfragen",
    description: "Die Anzahlung, die eine Bankettanfrage verlangt, bevor das Team zurückruft. Ausgeschaltet lassen, um keine zu verlangen.",
  },
  report: {
    title: "Anzahlungen",
    description:
      "Die letzten 30 Tage: verlangte und bezahlte Anzahlungen, das eingenommene Geld und wie oft Gäste mit und ohne bezahlte Anzahlung nicht erschienen sind.",
    requested: "Verlangt",
    paid: "Bezahlt",
    awaiting: "Ausstehend",
    expired: "Nicht rechtzeitig bezahlt",
    collected: "Eingenommen",
    refundDue: "Zu erstatten",
    noShowWith: "Nicht erschienen mit bezahlter Anzahlung",
    noShowWithout: "Nicht erschienen ohne Anzahlung",
    noShowCounts: "{noShows} von {finished} Besuchen",
    notEnoughData: "Noch nicht genug Daten: {finished} von {min} abgeschlossenen Besuchen",
    off: "Anzahlungen sind ausgeschaltet. Schalten Sie sie unter Einstellungen → Anzahlungen ein.",
    openSettings: "Einstellungen für Anzahlungen",
    loading: "Anzahlungen werden geladen…",
  },
};
