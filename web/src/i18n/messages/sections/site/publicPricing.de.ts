/** `publicPricing.*` in German: prices on the public site (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { publicPricingEn } from "./publicPricing.en";

export const publicPricingDe: Translation<typeof publicPricingEn> = {
  converted: "{price} pro Monat in Ihrer Währung",
  billedIn: "Tarife für dieses Land werden in {currency} abgerechnet.",
  conversionNote: "≈-Beträge dienen nur zur Orientierung: umgerechnet aus Euro nach {source}, Stand {date}; Sie zahlen in Euro.",
  rateSources: {
    nbg: "dem offiziellen Kurs der Nationalbank Georgiens",
    ecb: "dem Referenzkurs der Europäischen Zentralbank",
    official: "den offiziellen Kursen der Zentralbanken",
    planning: "dem Planungskurs der Plattform (kein Bankkurs)",
  },
  setup: {
    title: "Selbst einrichten oder von uns einrichten lassen",
    subtitle: "Derselbe Assistent in beiden Fällen. Sie wählen beim Abschluss.",
    selfTitle: "Selbst",
    selfPrice: "Kostenlos",
    selfPoints: {
      guide: "Eine Anleitung in acht kurzen Schritten, mit fertigen Antworten für Ihre Branche",
      test: "Ein Test-Chat und automatische Prüfungen vor dem Start",
      channels: "Sie verbinden die Kanäle mit Schritt-für-Schritt-Hilfe",
    },
    doneTitle: "Wir erledigen das",
    donePrice: "{price} einmalig",
    donePoints: {
      knowledge: "Wir tragen Ihre Preise, Speisekarte und Regeln von Ihrer Website oder aus Ihren Dateien ein",
      channels: "Wir verbinden Ihre Kanäle und die Anrufweiterleitung",
      launch: "Wir testen den Assistenten mit Ihnen und starten ihn gemeinsam",
    },
  },
  testimonials: {
    title: "Was Inhaber sagen",
  },
};
