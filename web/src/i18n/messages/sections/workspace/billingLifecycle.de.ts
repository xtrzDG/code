/** `billingLifecycle.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { billingLifecycleEn } from "./billingLifecycle.en";

export const billingLifecycleDe: Translation<typeof billingLifecycleEn> = {
  reasons: {
    too_expensive: "Es kostet zu viel",
    seasonal_break: "Wir haben Saisonpause",
    not_enough_use: "Gerade schreiben oder rufen zu wenige Kunden an",
    missing_feature: "Er kann etwas nicht, das wir brauchen",
    answer_quality: "Die Antworten sind nicht gut genug",
    switched_provider: "Wir wechseln zu einem anderen Dienst",
    closing_business: "Wir schließen das Unternehmen",
    somethingElse: "Etwas anderes",
  },
  cancel: {
    reasonLegend: "Was ist der Hauptgrund?",
    reasonHint: "Es hilft uns, besser zu werden, und vielleicht passt etwas besser zu Ihnen als eine Kündigung.",
    detailsLabel: "Möchten Sie etwas ergänzen?",
    detailsPlaceholder: "In Ihren eigenen Worten",
    continue: "Weiter",
    offerTitle: "Bevor Sie gehen",
    cancelAnyway: "Nein, trotzdem kündigen",
    back: "Zurück",
  },
  offerKinds: {
    pause: "Saisonpause",
    downgrade: "Günstigerer Tarif",
    credit: "Einmaliges Guthaben",
  },
  offers: {
    pause: {
      title: "Machen Sie stattdessen eine Saisonpause",
      description:
        "Ein pausierter Monat kostet {price}: Der Assistent nimmt weiter Anfragen auf, Ihre Kanäle bleiben verbunden, und der volle Service kommt von selbst zurück.",
      confirm: { one: "{count} Monat pausieren", other: "{count} Monate pausieren" },
    },
    downgrade: {
      title: "Behalten Sie Ihren Assistenten für weniger",
      description:
        "„{plan}“ kostet {price}. Ihre Antworten, Kanäle und Einstellungen bleiben, wie sie sind; der neue Preis gilt ab der nächsten Rechnung.",
      confirm: "Zu „{plan}“ wechseln",
    },
    credit: {
      title: "Bleiben Sie, {amount} gehen auf uns",
      description: "Wir schreiben Ihrem Konto {amount} gut; der Betrag wird von Ihrer nächsten Rechnung abgezogen.",
      confirm: "Guthaben annehmen",
    },
    taken: {
      pause: "Die Pause ist geplant",
      downgrade: "Der Tarif ist geändert",
      credit: "Das Guthaben ist auf Ihrem Konto",
    },
  },
  pause: {
    title: "Saisonpause",
    description:
      "Saisonbedingt geschlossen? Pausieren Sie statt zu kündigen: Der Assistent nimmt weiter Anfragen auf, Ihre Kanäle bleiben verbunden, und der volle Service kommt von selbst zurück.",
    price: "{price} pro Monat, {percent} % Ihres Tarifs",
    monthsLegend: "Wie lange",
    months: { one: "{count} Monat", other: "{count} Monate" },
    window: "Vom {start} bis {until}",
    submit: "Ab {date} pausieren",
    allowance: "Pausiert: {months} {window}.",
    allowanceMonths: { one: "{used} von {cap} Monat", other: "{used} von {cap} Monaten" },
    allowanceWindow: { one: "im letzten Monat", other: "in den letzten {window} Monaten" },
    scheduledTitle: "Pause geplant",
    scheduled:
      "Vom {start} bis {until} nimmt der Assistent nur Anfragen auf. Automatische Zahlungen sind aus; Zahlungen zum vollen Preis beginnen nach der Pause wieder.",
    callOff: "Pause absagen",
    calledOff: "Die Pause ist abgesagt",
    pausedTitle: "Pausiert bis {date}",
    paused: "Der Assistent nimmt nur Anfragen auf; Ihre Kanäle bleiben verbunden. Jeder pausierte Monat wird mit {percent} % Ihres Tarifs berechnet.",
    resume: "Vollen Service fortsetzen",
    resumeTitle: "Vollen Service jetzt fortsetzen?",
    resumeDescription:
      "Der Assistent antwortet Kunden wieder und nimmt Buchungen an. Ist dieser Pausenmonat schon bezahlt, kommt der volle Service zurück, wenn er endet; sonst jetzt, und der nächste Zeitraum wird fällig.",
    resumed: "Der volle Service kommt zurück",
    plansHint: "Während der Pause bleibt der Tarif, wie er ist; setzen Sie den vollen Service fort, um ihn zu ändern.",
    unavailable: {
      not_active: "Eine Pause ist für ein bezahltes Monatsabonnement möglich.",
      not_monthly: "Ein Jahrestarif kann nicht pausiert werden.",
      allowance_used: "In den letzten zwölf Monaten wurden vier Pausenmonate genutzt; Sie können später wieder pausieren.",
    },
  },
  facts: {
    pause: "Saisonpause",
  },
  errors: {
    offerGone: "Dieses Angebot ist nicht mehr verfügbar. Schließen Sie das Fenster und versuchen Sie es erneut.",
    pauseGone: "Eine Pause ist gerade nicht möglich. Laden Sie die Seite neu, um den Grund zu sehen.",
  },
};
