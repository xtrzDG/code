/** `phoneNumbers.*` texts of a phone number rented from the platform, in German. */

import type { Translation } from "../../../translate";
import type { phoneNumbersEn } from "./phoneNumbers.en";

export const phoneNumbersDe: Translation<typeof phoneNumbersEn> = {
  panel: {
    noNumber: "Noch keine Telefonnummer für Anrufe? Nehmen Sie eine von uns: Ihr Assistent nimmt dort sofort ab.",
    getNumber: "Nummer erhalten",
    rentedTitle: "Ihre Nummer von uns",
    monthly: "{price} pro Monat",
    answering: "Ihr Assistent nimmt ab",
    connecting: "Wird mit Ihrem Assistenten verbunden…",
    releasing: "Wird zurückgegeben",
    giveBackHint: "Um die Nummer zurückzugeben, trennen Sie den Telefonkanal. Sie wird nicht mehr berechnet und geht an den Anbieter zurück.",
    requestTitle: "Nummer angefragt",
    requestText: "Eine Nummer ({type}) in {country}. Unser Team kümmert sich darum und schreibt Ihnen; das kann einige Werktage dauern.",
    requestTextCity: "Eine Nummer ({type}) in {country}, in der Nähe von {city}. Unser Team kümmert sich darum und schreibt Ihnen; das kann einige Werktage dauern.",
    cancelRequest: "Anfrage zurückziehen",
    requestCancelled: "Anfrage zurückgezogen",
    ownerOnly: "Nur Inhaber können eine Nummer nehmen.",
  },
  tunnel: {
    title: "Anrufe",
    text: "Nehmen Sie eine Nummer von uns, und der Assistent nimmt dort Anrufe in der Sprache Ihrer Kunden an. Das geht auch später auf der Seite „Kanäle“.",
  },
  dialog: {
    title: "Telefonnummer erhalten",
    description: "Eine Nummer im Land Ihrer Wahl, monatlich mit Ihrem Tarif abgerechnet.",
    country: "Land",
    countriesNow: "Sofort erhältlich",
    countriesTeam: "Über unser Team",
    type: "Art der Nummer",
    city: "Stadt oder Region",
    cityHint: "Optional: Wir suchen Nummern in der Nähe.",
    search: "Nummern suchen",
    searching: "Nummern werden gesucht…",
    close: "Schließen",
  },
  types: {
    local: "Ortsnetz",
    mobile: "Mobil",
    toll_free: "gebührenfrei",
  },
  typeOptions: {
    local: "Ortsnetz (Festnetz)",
    mobile: "Mobil",
    toll_free: "Gebührenfrei für Anrufer",
  },
  offers: {
    title: "Nummern, die Sie jetzt nehmen können",
    price: "{price} pro Monat für jede davon",
    none: "Dort gibt es gerade keine freien Nummern dieser Art. Versuchen Sie es ohne Stadt, mit einer anderen Art, oder fragen Sie unser Team.",
    take: "Nehmen",
    takeLabel: "{number} nehmen",
  },
  confirm: {
    title: "{number} nehmen?",
    price: "Sie kostet {price} pro Monat und wird ab heute mit Ihrem Tarif abgerechnet.",
    channel: "Sie wird Ihr Telefonkanal, und Ihr Assistent nimmt dort ab.",
    giveBack: "Sie können sie jederzeit zurückgeben, indem Sie den Telefonkanal trennen.",
    take: "Nummer nehmen",
    back: "Zurück zur Liste",
    done: "{number} gehört jetzt Ihnen",
  },
  request: {
    requires_documents: "In diesem Land verlangt die Regulierungsbehörde Unterlagen Ihres Unternehmens, bevor eine Nummer vergeben wird. Unser Team erledigt das mit Ihnen.",
    on_request: "Nummern dieser Art besorgt unser Team hier von Hand.",
    ask: "Unser Team fragen",
    sent: "Anfrage gesendet: Unser Team schreibt Ihnen",
  },
  refusals: {
    numberTaken: "Diese Nummer wurde gerade vergeben. Suchen Sie erneut und wählen Sie eine andere.",
    priceChanged: "Der Preis für diese Art von Nummer hat sich geändert. Suchen Sie erneut, um den neuen Preis zu sehen.",
  },
};
