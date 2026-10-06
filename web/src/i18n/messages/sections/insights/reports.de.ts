/** `reports.*` in German: Overview → Reports (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { reportsEn } from "./reports.en";

export const reportsDe: Translation<typeof reportsEn> = {
  description: "Was der Assistent in jedem Monat und jeder Woche getan hat, und die Zusammenfassungen, die Sie darüber bekommen.",
  loading: "Die Berichte werden geladen…",
  opened: "Aus Ihrer Zusammenfassung",
  past: "Frühere Berichte",
  kindLabel: "Art des Berichts",
  kinds: {
    monthly: "Monatlich",
    weekly: "Wöchentlich",
    daily: "Täglich",
  },
  empty: {
    title: "Noch keine Berichte",
    monthly: "Der erste Monatsbericht entsteht am 1., über den Vormonat.",
    weekly: "Wochenzusammenfassungen entstehen montags, über die Vorwoche.",
    daily: "Tageszusammenfassungen entstehen jeden Morgen für Inhaber, die sie eingeschaltet haben.",
  },
  monthSoFar: {
    title: "Dieser Monat bisher",
    next: "Der vollständige Bericht kommt am {date}",
  },
  summary: {
    bookings: { one: "{count} Buchung", other: "{count} Buchungen" },
    requests: { one: "{count} Anfrage", other: "{count} Anfragen" },
  },
  delivery: {
    sent: { one: "An {count} Inhaber gesendet", other: "An {count} Inhaber gesendet" },
    quiet: "Nicht gesendet: eine ruhige Zeit",
    noRecipients: "Niemand hatte es eingeschaltet",
  },
  details: {
    toggle: "Alle Zahlen",
    caption: "Die Zahlen des Berichts im Vergleich zum Vorzeitraum",
    measure: "Was",
    change: "Veränderung",
    before: "vorher: {value}",
    noCheck: "Es wurde kein durchschnittlicher Bon festgelegt, daher enthält der Bericht keine Geldschätzung.",
    ownerCheck: "Geld geschätzt mit Ihrem durchschnittlichen Bon von {money}.",
    typicalCheck: "Geld geschätzt mit dem für Ihre Branche typischen Bon von {money}.",
    bookedPrices: "Geld aus den Preisen des Gebuchten.",
    mixedCheck: "Geld aus den Preisen des Gebuchten; Buchungen ohne Preis zum durchschnittlichen Bon von {money}.",
  },
  rows: {
    assistantBookings: "Buchungen durch den Assistenten",
    estimate: "Wert (Schätzung)",
    staffTime: "Eingesparte Arbeitszeit",
    afterHours: "Gespräche außerhalb der Zeiten",
    conversations: "Gespräche",
    customerMessages: "Nachrichten von Kunden",
    assistantReplies: "Antworten des Assistenten",
    calls: "Angenommene Anrufe",
    bookings: "Alle Buchungen",
    requests: "Anfragen",
    handoffs: "Brauchten eine Person",
  },
  duration: {
    hoursMinutes: "{hours} Std. {minutes} Min.",
    minutes: "{minutes} Min.",
  },
  digests: {
    title: "Ihre Zusammenfassungen",
    description: "Was der Assistent getan hat, in Ihrer Sprache an Sie gesendet, mit einem Link hierher zurück.",
    monthly: "Monatsbericht",
    monthlyHint: "Am 1. um 9:00, über den Vormonat",
    weekly: "Wochenzusammenfassung",
    weeklyHint: "Montags um 9:00, über die Vorwoche",
    daily: "Tageszusammenfassung",
    dailyHint: "Jeden Morgen um 9:00, über den Vortag",
  },
};
