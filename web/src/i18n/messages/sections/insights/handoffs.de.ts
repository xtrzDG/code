/** `handoffs.*` in German: conversations that need a person (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { handoffsEn } from "./handoffs.en";

export const handoffsDe: Translation<typeof handoffsEn> = {
  urgency: {
    critical: "Kritisch",
    high: "Dringend",
    normal: "Normal",
    low: "Niedrig",
  },
  reason: {
    customer_request: "Hat nach einer Person gefragt",
    complaint: "Beschwerde",
    vip_guest: "VIP-Gast",
    non_standard_request: "Ungewöhnlicher Wunsch",
    unknown_answer: "Der Assistent kannte die Antwort nicht",
    emergency: "Notfall",
    sensitive_topic: "Heikles Thema",
    profile_rule: "Eine Ihrer Regeln",
    unverified_numbers: "Unbestätigte Preise oder Zahlen",
  },
  status: {
    pending: "Team wird benachrichtigt",
    notified: "Team benachrichtigt",
    notification_failed: "Benachrichtigung fehlgeschlagen",
    resolved: "Erledigt",
  },
  notificationFailedHint: "Das Team hat die Benachrichtigung nicht bekommen. Rufen Sie den Kunden zurück und prüfen Sie die Kontakte in den Einstellungen.",
  summaryCodes: {
    model_declined: "Der Assistent wollte diese Nachricht nicht beantworten.",
    model_unavailable: "Der Assistent war kurz nicht verfügbar und konnte nicht antworten.",
    answer_unfinished: "Der Assistent konnte seine Antwort nicht beenden.",
    unverified_values: "Der Assistent hat eine Antwort mit Zahlen oder Aussagen zurückgehalten, die nicht in Ihren Unternehmensangaben stehen.",
    call_booking_unverified_values:
      "Im Anruf hat der Assistent Zahlen genannt, die nicht in Ihren Unternehmensangaben stehen. Prüfen Sie die Buchung aus diesem Anruf anhand des Transkripts.",
    call_request_unverified_values:
      "Im Anruf hat der Assistent Zahlen genannt, die nicht in Ihren Unternehmensangaben stehen. Prüfen Sie die Anfrage aus diesem Anruf anhand des Transkripts.",
    reply_undelivered: "Die Antwort des Assistenten hat den Kunden nicht erreicht. Kontaktieren Sie ihn auf anderem Weg.",
    data_erased: "Angaben auf Wunsch des Kunden gelöscht.",
  },
  summaryCodesWithValues: {
    unverified_values: "Der Assistent hat eine Antwort mit Zahlen oder Aussagen zurückgehalten, die nicht in Ihren Unternehmensangaben stehen ({values}).",
    call_booking_unverified_values:
      "Im Anruf hat der Assistent Zahlen genannt, die nicht in Ihren Unternehmensangaben stehen ({values}). Prüfen Sie die Buchung aus diesem Anruf anhand des Transkripts.",
    call_request_unverified_values:
      "Im Anruf hat der Assistent Zahlen genannt, die nicht in Ihren Unternehmensangaben stehen ({values}). Prüfen Sie die Anfrage aus diesem Anruf anhand des Transkripts.",
  },
  quote: {
    customer: "Die Nachricht des Kunden",
    reply: "Die Antwort, die nicht angekommen ist",
  },
};
