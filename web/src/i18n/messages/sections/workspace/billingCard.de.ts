/** `billingCard.*` texts of Settings → Billing: the card on file, the retries of a declined payment and the trial's "Save card" prompt, in German. */

import type { Translation } from "../../../translate";
import type { billingCardEn } from "./billingCard.en";

export const billingCardDe: Translation<typeof billingCardEn> = {
  title: "Karte für Zahlungen",
  description: "Die automatischen Zahlungen des Abos werden von dieser Karte abgebucht.",
  endingIn: "Karte mit der Endung {digits}",
  expires: "Gültig bis {date}",
  noExpiry: "Ablaufdatum nicht übermittelt",
  expiryStates: {
    expired: "Abgelaufen",
    expiring: "Läuft bald ab",
  },
  facts: {
    provider: "Zahlungsdienst",
    savedAt: "Gespeichert am",
  },
  noCard: "Noch keine Karte gespeichert",
  noCardTrial: "Speichern Sie eine Karte, dann läuft das Abo nach dem Testzeitraum von selbst weiter.",
  noCardPaid: "Speichern Sie eine Karte, damit die nächsten Zahlungen von selbst laufen.",
  cardWithoutDetails: "Bei {provider} ist eine Karte gespeichert. Ihre Angaben erscheinen hier nach der nächsten Zahlung.",
  expiredHint: "Diese Karte ist abgelaufen. Speichern Sie vor der nächsten Zahlung eine neue.",
  expiringHint: "Diese Karte läuft bald ab. Speichern Sie eine neue, damit die nächste Zahlung durchgeht.",
  noCharge: "Beim Speichern wird nichts abgebucht: Der Zahlungsdienst prüft die Karte nur.",
  payToSave: "Wenn Sie die offene Rechnung bezahlen, wird die Karte gespeichert, mit der Sie zahlen.",
  setupFeeNow: "Beim Speichern der Karte wird jetzt die einmalige Einrichtungsgebühr von {amount} abgebucht. Die monatlichen Zahlungen beginnen nach dem Testzeitraum.",
  retryUsesNewCard: "Der nächste Versuch belastet die Karte, die Sie speichern.",
  save: "Karte speichern",
  update: "Karte ändern",
  opening: "Wird geöffnet…",
  retry: {
    title: "Die automatische Zahlung ist nicht durchgegangen",
    declined: "Die Karte wurde abgelehnt. Wir versuchen es von selbst noch einmal.",
    outcomes: {
      claimed: "Versuch {attempt} von {total} läuft.",
      approved: "Versuch {attempt} von {total} ist durchgegangen. Die Zahlung wird bestätigt.",
      declined: "Versuch {attempt} von {total} wurde abgelehnt.",
      processing: "Versuch {attempt} von {total} wird bearbeitet.",
      failed: "Versuch {attempt} von {total} hat den Zahlungsdienst nicht erreicht.",
      not_possible: "Versuch {attempt} von {total} war nicht möglich: Es ist keine Karte gespeichert.",
      skipped: "Versuch {attempt} von {total} wurde übersprungen.",
    },
    next: "Nächster Versuch: {date}",
    noMore: "Es folgen keine weiteren Versuche. Ab {date} nimmt der Assistent nur noch Anfragen an.",
  },
  trialPrompt: {
    title: { one: "Noch {count} Tag Testzeitraum", other: "Noch {count} Tage Testzeitraum" },
    body: "Bis zum {date} wird nichts abgebucht: Speichern Sie jetzt eine Karte, dann antwortet der Assistent auch nach dem Testzeitraum weiter.",
    bodyWithSetupFee: "Speichern Sie jetzt eine Karte: Sie zahlt die einmalige Einrichtungsgebühr von {amount}, und ab dem {date} laufen die monatlichen Zahlungen darüber. Der Assistent antwortet auch nach dem Testzeitraum weiter.",
  },
  returned: {
    title: "Ihre Karte wird gespeichert",
    pending: "Die Karte erscheint hier, sobald der Zahlungsdienst sie bestätigt, meist innerhalb einer Minute.",
    savedTitle: "Karte gespeichert",
    saved: "Die automatischen Zahlungen werden jetzt von dieser Karte abgebucht.",
  },
  errors: {
    cannotSave: "Gerade kann keine Karte gespeichert werden. Bezahlen Sie die offene Rechnung: Damit wird die Karte gespeichert, mit der Sie zahlen.",
  },
};
