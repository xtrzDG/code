/** `reviewSettings.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { reviewSettingsEn } from "./reviewSettings.en";

export const reviewSettingsDe: Translation<typeof reviewSettingsEn> = {
  description: "Fragen Sie Kunden, wie ihr Besuch war, laden Sie alle ein, Sie auf Google zu bewerten, und sehen Sie, was sie geantwortet haben.",
  stats: {
    title: "Letzte 30 Tage",
    description: "Nach ihrem Besuch gefragte Kunden und was sie geantwortet haben.",
    asked: "Gefragt",
    answered: "Geantwortet",
    answeredShare: "{percent} der Gefragten",
    average: "Durchschnittliche Bewertung",
    averageValue: "{score} von 5",
    noAverage: "Noch keine Bewertungen",
    opened: "Bewertungslink geöffnet",
    notTracked: "Auf dieser Plattform nicht gezählt",
    scores: "Bewertungen",
    scoreRow: { one: "{score} Stern: {count}", other: "{score} Sterne: {count}" },
    notAsked: "Nicht gefragt: {count}",
    notDelivered: "Nicht zugestellt: {count}",
  },
  feedback: {
    title: "Feedback nach Besuchen",
    description:
      "Nach einem abgeschlossenen Besuch bitten wir den Kunden, ihn von 1 bis 5 zu bewerten, im genutzten Messenger und in seiner Sprache. Die Plattform beantwortet die Bewertung selbst: Sie bedankt sich und sendet Ihren Bewertungslink.",
    toggle: "Kunden fragen, wie ihr Besuch war",
    turnedOff: "Kunden werden nicht mehr nach ihrem Besuch gefragt",
    delay: "Wann gefragt wird",
    delayHint: "Gezählt ab dem Ende der Buchung.",
    delayMinutes: { one: "{count} Minute nach dem Besuch", other: "{count} Minuten nach dem Besuch" },
    delayHours: { one: "{count} Stunde nach dem Besuch", other: "{count} Stunden nach dem Besuch" },
    delayDays: { one: "{count} Tag nach dem Besuch", other: "{count} Tage nach dem Besuch" },
    template: "Name der WhatsApp-Vorlage",
    templateHint:
      "Für WhatsApp-Kunden, die seit 24 Stunden nicht geschrieben haben: die genehmigte Utility-Vorlage auf Ihrer Nummer (lateinische Kleinbuchstaben, Ziffern und Unterstriche).",
    templateInvalid: "Verwenden Sie nur lateinische Kleinbuchstaben, Ziffern und Unterstriche.",
    readiness: {
      off: "Feedback-Anfragen sind aus.",
      everywhere: "Kunden werden in Telegram, WhatsApp, Messenger und Instagram gefragt; WhatsApp-Kunden, die einen Tag still waren, bekommen Ihre Vorlage.",
      window: "Kunden werden innerhalb von 24 Stunden nach ihrer letzten Nachricht gefragt; länger stille WhatsApp-Kunden werden übersprungen, bis die Vorlage festgelegt ist.",
    },
    whatsappMissing: "WhatsApp ist nicht verbunden.",
    connectWhatsapp: "WhatsApp verbinden",
    rules:
      "Zu jedem Besuch wird einmal gefragt, und jeder Kunde höchstens einmal am Tag. Kunden, die STOP geantwortet haben, bekommen keine Anfragen. Eine Bewertung von 3 oder weniger geht auch an Posteingang → Braucht eine Person, damit sich jemand meldet.",
  },
  link: {
    title: "Google-Bewertungslink",
    description:
      "Alle, die antworten, bekommen diesen Link mit dem Dank, unabhängig von ihrer Bewertung: Nur zufriedene Kunden einzuladen verstößt gegen die Regeln von Google.",
    label: "Link zu Ihrer Google-Bewertungsseite",
    hint: "Wählen Sie im Google-Unternehmensprofil „Nach Rezensionen fragen“ und kopieren Sie den Link.",
    invalid: "Geben Sie einen vollständigen Link ein, der mit https:// beginnt",
    tracked: "Wir senden ihn über die Kurzadresse der Plattform, um zu zählen, wie viele Kunden ihn öffnen.",
    missing: "Ohne Link bekommen Kunden nur einen Dank.",
  },
  template: {
    title: "Text der Vorlage",
    description:
      "Legen Sie im Meta Business Manager eine WhatsApp-Utility-Vorlage mit diesem Text an, eine Übersetzung pro Sprache; ihr einziger Parameter ist der Name Ihres Unternehmens. Kunden bekommen sie in ihrer Sprache oder auf Englisch, wenn es keine Übersetzung gibt.",
    body: "Text für die Vorlage",
    example: "Was Kunden lesen",
  },
  requests: {
    title: "Neueste Anfragen",
    description: "Die letzten 20 Besuche, zu denen wir gefragt haben, und was Kunden geantwortet haben.",
    empty: "Noch keine Anfragen",
    emptyDescription: "Kunden werden nach ihren Besuchen gefragt, sobald Feedback eingeschaltet ist.",
    customer: "Kunde",
    visitEnded: "Besuch beendet {time}",
    rating: "Bewertet mit {score} von 5",
    openedLink: "Bewertungslink geöffnet",
    openConversation: "Gespräch öffnen",
    notAskedBecause: "Nicht gefragt: {reason}",
    statuses: {
      sent: "Wartet auf Antwort",
      answered: "Geantwortet",
      skipped: "Nicht gefragt",
      failed: "Nicht zugestellt",
    },
    skipReasons: {
      opted_out: "der Kunde hat STOP geantwortet",
      no_contact: "die Angaben des Kunden wurden gelöscht",
      no_channel: "kein Messenger zum Schreiben",
      window_closed: "WhatsApp braucht nach 24 Stunden die genehmigte Vorlage",
      already_asked: "heute schon gefragt",
      daily_limit: "das Tageslimit für Nachrichten war erreicht",
    },
  },
};
