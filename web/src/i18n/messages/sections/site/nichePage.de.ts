/** `nichePage.*` in German: a public page for one kind of business (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { nichePageEn } from "./nichePage.en";

export const nichePageDe: Translation<typeof nichePageEn> = {
  metaTitle: "{niche}: ein KI-Assistent für Anrufe und Nachrichten",
  metaDescription:
    "{description} Der Assistent antwortet Tag und Nacht in den Sprachen Ihrer Kunden, nimmt Buchungen und Anfragen an und gibt komplexe Fälle an Ihr Team weiter.",
  breadcrumb: "Branchen",
  eyebrow: "Ein KI-Assistent für diese Branche",
  title: "{niche}: jeder Anruf und jede Nachricht beantwortet",
  lead: "Der Assistent weiß, was Kunden dieser Branche üblicherweise fragen, antwortet nach Ihren eigenen Preisen und Regeln und erfindet nie etwas.",
  primary: "Assistenten erstellen",
  secondary: "Demo ausprobieren",
  doesTitle: "Was der Assistent hier macht",
  books: "Bucht: {resource}, passend zu Ihren Zeiten und freien Plätzen",
  noBookings: "Nimmt Bestellungen und Anfragen mit den Angaben auf, die Ihr Team braucht",
  answers: "Beantwortet Fragen zu Preisen, Zeiten und Regeln in der Sprache des Kunden",
  handoff: "Gibt Beschwerden und ungewöhnliche Wünsche mit einer kurzen Zusammenfassung an eine Person weiter",
  sensitive: "Heikle Fragen (Gesundheit, Sicherheit, Recht) gehen immer an eine Person: Der Assistent berät dazu nicht",
  integrationsTitle: "Funktioniert mit",
  plansTitle: "Passende Tarife",
  plansText: "Unternehmen wie dieses beginnen meist mit {plans}. Jeder Tarif hat eine kostenlose Testphase.",
  pricingLink: "Preise ansehen",
  demoTitle: "Sprechen Sie mit einem Demo-Assistenten",
  demoText: "Ein Demo-Unternehmen dieser Branche antwortet wie ein echtes; nichts wird wirklich gebucht.",
  otherTitle: "Andere Branchen",
  notFound: "Diese Branche gibt es nicht.",
};
