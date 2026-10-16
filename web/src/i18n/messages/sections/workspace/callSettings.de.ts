/** `callSettings.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { callSettingsEn } from "./callSettings.en";

export const callSettingsDe: Translation<typeof callSettingsEn> = {
  description: "Was nach jedem Anruf passiert: eine Zusammenfassung für Ihr Team und eine Nachricht an Anrufer, die nicht durchgekommen sind.",
  summaries: {
    title: "Anrufzusammenfassungen",
    description:
      "Nach jedem Anruf bekommen die Team-Chats in Telegram und WhatsApp, wer angerufen hat, was er wollte, wie der Anruf endete und alles, was der Assistent gesagt hat und nicht in Ihren Daten steht. Anrufer, die nicht durchgekommen sind, werden auf jedem Kanal gemeldet, damit jemand zurückruft.",
    toggle: "Nach jedem Anruf eine Zusammenfassung senden",
    contactsHint: "Wer sie bekommt: die Kontakte im Team unter Einstellungen → Benachrichtigungen.",
    openContacts: "Kontakte im Team",
    turnedOff: "Anrufzusammenfassungen sind aus",
  },
  textBack: {
    title: "Verpassten Anrufern schreiben",
    description:
      "Wenn ein Anrufer nicht durchkommt (die Leitung ist besetzt, niemand nimmt ab, er legt früh auf, der Assistent kann den Anruf nicht annehmen oder niemand nimmt eine Weiterleitung an), schreiben wir ihm innerhalb von ein bis zwei Minuten in seiner Sprache. Seine Antwort geht als WhatsApp-Gespräch im Posteingang weiter.",
    toggle: "Anrufern schreiben, die nicht durchgekommen sind",
    template: "Name der WhatsApp-Vorlage",
    templateHint: "Der Name der genehmigten Utility-Vorlage auf Ihrer WhatsApp-Nummer: lateinische Kleinbuchstaben, Ziffern und Unterstriche.",
    templateInvalid: "Verwenden Sie nur lateinische Kleinbuchstaben, Ziffern und Unterstriche.",
    sms: "Eine SMS senden, wenn WhatsApp nicht möglich ist",
    smsHint: "Vom SMS-Absender der Plattform, wenn die Nummer kein WhatsApp hat oder die Vorlage abgelehnt wird.",
    smsNeedsTextBack: "Schalten Sie zuerst die Nachrichten an Anrufer ein, die nicht durchgekommen sind.",
    rules: "Jeder Anrufer bekommt höchstens einmal am Tag eine Nachricht. Kunden, die Nachrichten abbestellt haben oder Ihnen bereits schreiben, bekommen keine.",
    turnedOff: "Nachrichten an Anrufer, die nicht durchgekommen sind, sind aus",
    smsTurnedOff: "SMS an Anrufer, die nicht durchgekommen sind, sind aus",
    readiness: {
      whatsapp: "Anrufer bekommen Ihre WhatsApp-Vorlage.",
      sms: "Anrufer bekommen eine SMS.",
      none: "Noch kann nichts gesendet werden: Verbinden Sie WhatsApp und benennen Sie die Vorlage, oder erlauben Sie SMS.",
      off: "Rückmeldungen sind aus.",
    },
    whatsappMissing: "WhatsApp ist nicht verbunden.",
    connectWhatsapp: "WhatsApp verbinden",
    smsMissing: "SMS ist auf dieser Plattform nicht eingerichtet.",
  },
  template: {
    title: "Text der Vorlage",
    description:
      "Legen Sie im Meta Business Manager eine WhatsApp-Utility-Vorlage mit diesem Text an, eine Übersetzung pro Sprache; ihr einziger Parameter ist der Name Ihres Unternehmens. Anrufer bekommen sie in ihrer Sprache oder auf Englisch, wenn es keine Übersetzung gibt.",
    body: "Text für die Vorlage",
    example: "Was Anrufer lesen",
  },
  history: {
    title: "Letzte Rückmeldungen",
    description: "Die letzten 20 Anrufer, die nicht durchgekommen sind, und was ihnen gesendet wurde.",
    empty: "Noch keine verpassten Anrufe",
    emptyDescription: "Anrufer, die nicht durchkommen, erscheinen hier.",
    hiddenNumber: "Unterdrückte Nummer",
    openConversation: "Gespräch öffnen",
    notSentBecause: "Nicht gesendet: {reason}",
    statuses: {
      queued: "Wird gesendet",
      sent: "Gesendet",
      failed: "Nicht zugestellt",
      skipped: "Nicht gesendet",
    },
    channels: {
      whatsapp: "WhatsApp",
      sms: "SMS",
    },
    reasons: {
      no_answer: "Keine Antwort",
      busy: "Leitung besetzt",
      abandoned: "Vor der Annahme aufgelegt",
      line_failed: "Anruf nicht verbunden",
      not_started: "Der Assistent konnte den Anruf nicht annehmen",
      no_speech: "Ohne zu sprechen aufgelegt",
      transfer_unanswered: "Weiterleitung nicht angenommen",
    },
    skipReasons: {
      turned_off: "Rückmeldungen waren aus",
      opted_out: "der Kunde hat Nachrichten abbestellt",
      already_texted: "heute schon angeschrieben",
      daily_limit: "das Tageslimit war erreicht",
      in_conversation: "er schreibt Ihnen bereits",
      no_channel: "kein Kanal zum Senden",
      not_live: "der Assistent war nicht live",
      no_caller_number: "die Nummer war unterdrückt",
      too_late: "der Anruf wurde zu spät gemeldet",
    },
  },
};
