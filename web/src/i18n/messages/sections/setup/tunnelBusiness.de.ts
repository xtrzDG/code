/** `tunnelBusiness.*` in German: the tunnel's first two steps (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { tunnelBusinessEn } from "./tunnelBusiness.en";

export const tunnelBusinessDe: Translation<typeof tunnelBusinessEn> = {
  business: {
    title: "Wie heißt Ihr Unternehmen?",
    text: "Wir erstellen einen Assistenten, der Ihren Kunden für Sie antwortet, Tag und Nacht.",
    name: "Name des Unternehmens",
    namePlaceholder: "Zum Beispiel Salon Morgenrot",
    kindTitle: "Was machen Sie?",
    kindHint: "Wählen Sie das Nächstliegende. Es bestimmt, was Ihr Assistent fragt, bucht und weiß.",
    kindFixed: "Das haben Sie beim Erstellen des Assistenten gewählt; es lässt sich nicht ändern.",
    legalReview: "Unternehmen dieser Art durchlaufen eine kurze rechtliche Prüfung, bevor der Assistent live geht.",
    detailsTitle: "Noch etwas, das Kunden immer fragen",
    errors: {
      name: "Geben Sie den Namen Ihres Unternehmens ein.",
      kind: "Wählen Sie, was Ihr Unternehmen macht.",
    },
  },
  place: {
    title: "Wo sind Sie?",
    text: "Ihr Land bestimmt die Währung, die Zeitzone und die Sprachen Ihrer Kunden. Wir haben ausgefüllt, was wir konnten.",
    country: "Land",
    countryHint: "Preise in {currency}",
    countryFixed: "Das Land lässt sich nicht mehr ändern, sobald der Assistent existiert.",
    city: "Stadt",
    cityPlaceholder: "Zum Beispiel Berlin",
    address: "Adresse",
    addressPlaceholder: "Straße und Hausnummer",
    addressHint: "Der Assistent erklärt Kunden, wie sie Sie finden.",
    addressOptional: "optional",
    languages: "Sprachen, in denen Ihre Kunden schreiben",
    languagesHint: "Der Assistent antwortet jedem Kunden in seiner Sprache, unter diesen.",
    defaultLanguage: "Erste Begrüßung auf",
    timezone: "Zeitzone",
    creating: "Ihr Assistent wird erstellt…",
    errors: {
      country: "Wählen Sie Ihr Land.",
      languages: "Wählen Sie mindestens eine Sprache.",
      address: "Geben Sie Ihre Adresse ein: Kunden brauchen sie, um Sie zu finden.",
      restricted: "Unternehmen aus diesem Land können noch nicht erstellt werden.",
    },
  },
};
