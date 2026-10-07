/** `adminActions.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminActionsEn } from "./adminActions.en";

export const adminActionsDe: Translation<typeof adminActionsEn> = {
  menu: "Kontoaktionen",
  reasonLabel: "Warum",
  reasonHint: "Das Protokoll des Kunden speichert es, mit Ihrem Namen.",
  reasonShort: "Begründen Sie mit mindestens 8 Zeichen.",
  done: "Im Konto des Kunden gespeichert",
  autoDebitNote:
    "Dieser Kunde zahlt automatisch: Die Karte wird weiter mit dem beim Abschluss vereinbarten Betrag belastet. Rabatte und Guthaben gelten für Rechnungen, die im Dashboard oder per Überweisung bezahlt werden.",
  extend: {
    action: "Testphase verlängern",
    title: "Testphase von {name} verlängern",
    description:
      "Eine laufende Testphase endet später; eine unbezahlt beendete Testphase beginnt ab heute neu, ihre Rechnungen werden storniert und der volle Service kommt zurück.",
    days: "Zusätzliche Tage",
    daysHint: "1 bis 60 Tage.",
    daysInvalid: "Geben Sie eine ganze Zahl von 1 bis 60 Tagen ein.",
    confirm: "Verlängern",
  },
  discount: {
    action: "Rabatt geben",
    title: "Ein Rabatt für {name}",
    description:
      "Zeiträume, die spätestens am letzten Tag beginnen, werden mit diesem Abschlag vom Preis vor Steuern berechnet. Ein neuer Rabatt ersetzt den aktuellen.",
    percent: "Rabatt, %",
    percentInvalid: "Geben Sie einen ganzen Prozentwert von 1 bis 100 ein.",
    lastDay: "Letzter Tag",
    lastDayHint: "In der Zeitzone des Kunden; höchstens drei Jahre im Voraus.",
    lastDayInvalid: "Wählen Sie einen Tag ab heute.",
    confirm: "Rabatt geben",
  },
  credit: {
    action: "Guthaben gewähren",
    title: "Guthaben für {name}",
    description: "Guthaben wird vor Steuern vom Preis der nächsten Rechnungen abgezogen, bis es aufgebraucht ist. Eine stornierte Rechnung gibt ihr Guthaben zurück.",
    amount: "Betrag, {currency}",
    amountInvalid: "Geben Sie einen Betrag über null ein (höchstens zwei Nachkommastellen).",
    confirm: "Guthaben gewähren",
  },
  waive: {
    action: "Einrichtungsgebühr erlassen",
    title: "Einrichtungsgebühr von {name} erlassen?",
    description:
      "Die unbezahlte Rechnung der Einrichtungsgebühr wird storniert, und es wird keine Einrichtungsgebühr mehr berechnet. Eine bereits bezahlte Gebühr wird über den Zahlungsanbieter erstattet, nicht hier.",
    confirm: "Gebühr erlassen",
  },
  payment: {
    action: "Zahlung erfassen",
    title: "Zahlung von {name} erfassen",
    description:
      "Geld, das außerhalb der Kartenzahlung eingegangen ist, bezahlt jetzt eine offene Rechnung. Ein bezahlter Zeitraum bringt den vollen Service zurück, wie eine Kartenzahlung.",
    invoice: "Rechnung",
    noOpenInvoices: "Der Kunde hat keine offenen Rechnungen.",
    method: "Wie es eingegangen ist",
    methods: {
      bank_transfer: "Banküberweisung",
      cash: "Bar",
    },
    reference: "Referenz",
    referenceHint: "Die Referenz auf dem Kontoauszug oder die Nummer des Barbelegs.",
    referenceInvalid: "Geben Sie die Referenz ein (bis zu 120 Zeichen).",
    confirm: "Als bezahlt markieren",
  },
  plan: {
    action: "Tarif ändern",
    title: "Tarif von {name} ändern",
    description:
      "Die nächste Rechnung nutzt den Preis aus der Preisliste, ohne Bezahlvorgang. Ändert sich der abgebuchte Betrag, stoppen automatische Zahlungen und unbezahlte Rechnungen zum alten Preis werden storniert; ein Tarif ohne Sprache schaltet den Sprachagenten aus.",
    plan: "Tarif",
    period: "Abrechnung",
    confirm: "Tarif ändern",
  },
  account: {
    title: "Dem Kunden gewährt",
    description: "Was das Plattform-Team diesem Konto gegeben hat: die Testphase, einen Rabatt, Guthaben und die Einrichtungsgebühr.",
    trialEnds: "Testphase endet",
    noTrial: "Keine laufende Testphase",
    discount: "Rabatt",
    discountActive: "{percent} Rabatt auf Zeiträume, die bis {date} beginnen",
    discountEnded: "{percent}, beendet {date}",
    noDiscount: "Keiner",
    credit: "Verbleibendes Guthaben",
    setupFee: "Einrichtungsgebühr",
    setupFeeWaived: "Erlassen",
    setupFeeCharged: "Wird berechnet, wenn sie anfällt",
    noSubscription: "Der Kunde hat noch kein Abonnement: Kontoaktionen warten darauf.",
  },
  onboarding: {
    title: "Einrichtung durch uns angefragt",
    description: "Am {date} hat der Inhaber das Plattform-Team gebeten, das Unternehmen einzurichten ({plan}).",
    markDone: "Als erledigt markieren",
    marked: "Die Einrichtung durch uns ist als erledigt markiert",
  },
};
