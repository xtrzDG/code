/** `metaConnect.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { metaConnectEn } from "./metaConnect.en";

export const metaConnectDe: Translation<typeof metaConnectEn> = {
  continue: "Mit Facebook fortfahren",
  intro: {
    whatsapp:
      "Melden Sie sich mit Facebook an und wählen oder erstellen Sie im Facebook-Fenster Ihr WhatsApp-Business-Konto und Ihre Nummer. Die Nummer verbinden wir selbst.",
    instagram:
      "Melden Sie sich mit Facebook an und wählen Sie die Seite, mit der Ihr professionelles Instagram-Konto verknüpft ist. Den Rest erledigen wir.",
    messenger: "Melden Sie sich mit Facebook an und wählen Sie die Seite, deren Messenger-Chats der Assistent beantwortet.",
  },
  orManual: "Sie haben die IDs und den Schlüssel schon? Sie können sie weiterhin von Hand eingeben.",
  preparing: "Facebook wird vorbereitet…",
  starting: "Wird gestartet…",
  openWindow: "Facebook-Fenster öffnen",
  openHint: "Ihr Browser wartet auf einen Klick: Die Anmeldung bei Facebook öffnet sich in einem neuen Fenster.",
  waiting: "Schließen Sie die Anmeldung im Facebook-Fenster ab. Dieser Dialog wartet darauf.",
  finishing: "Wird verbunden…",
  notices: {
    cancelled: "Das Facebook-Fenster wurde vor dem Ende geschlossen. Versuchen Sie es erneut, wenn Sie bereit sind.",
    failed: "Facebook konnte die Einrichtung nicht abschließen. Versuchen Sie es erneut oder geben Sie die Angaben manuell ein.",
    unavailable:
      "Die Anmeldung mit Facebook wurde nicht geladen (ein Werbe- oder Tracking-Blocker kann sie verhindern). Versuchen Sie es später oder geben Sie die Angaben manuell ein.",
  },
  pages: {
    title: "Seite wählen",
    hint: "Die Seiten, die Sie auf Facebook verwalten.",
    instagramHint: "Instagram lässt sich nur über eine Seite verbinden, mit der ein professionelles Instagram-Konto verknüpft ist.",
    none: "Facebook zeigt keine Seite, die Sie verwalten. Beginnen Sie neu und markieren Sie im Facebook-Fenster die Seite Ihres Unternehmens.",
    instagram: "Instagram: @{username}",
    instagramNoName: "Instagram verknüpft",
    noInstagram: "Kein Instagram verknüpft",
    connect: "Diese Seite verbinden",
    connecting: "Wird verbunden…",
  },
  refusals: {
    meta_link_expired: "Diese Anmeldung mit Facebook ist abgelaufen. Beginnen Sie neu.",
    meta_not_configured: "Die Anmeldung mit Facebook ist auf diesem Server nicht eingerichtet. Geben Sie die Angaben manuell ein.",
    meta_permission_missing:
      "Facebook hat nicht alle nötigen Berechtigungen erteilt. Beginnen Sie neu und lassen Sie alle Häkchen gesetzt.",
    whatsapp_account_missing:
      "Facebook hat kein WhatsApp-Business-Konto zurückgegeben. Beginnen Sie neu und wählen oder erstellen Sie eines.",
    whatsapp_number_missing: "Dieses WhatsApp-Business-Konto hat noch keine Telefonnummer. Fügen Sie im Facebook-Fenster eine hinzu.",
    whatsapp_pin_mismatch:
      "Für diese Nummer ist die Bestätigung in zwei Schritten mit einer anderen PIN aktiv. Schalten Sie sie im WhatsApp Manager aus und versuchen Sie es erneut.",
    meta_page_not_found: "Facebook hat keinen Zugriff auf diese Seite gewährt. Beginnen Sie neu und markieren Sie sie im Facebook-Fenster.",
    instagram_account_missing:
      "Mit dieser Seite ist kein professionelles Instagram-Konto verknüpft. Verknüpfen Sie eines in den Instagram-Einstellungen oder wählen Sie eine andere Seite.",
  },
  commentReplies: {
    title: "Antworten auf Kommentare",
    toggle: "Kommentare mit einem Stichwort per Direct beantworten",
    description:
      "Schreibt jemand eines Ihrer Stichwörter in einen Kommentar unter einem Beitrag, schickt der Assistent dieser Person eine Nachricht per Direct. Höchstens eine pro Tag und Person und 60 pro Stunde.",
    unavailable: "Antworten auf Kommentare starten mit dem nächsten Update des Dienstes. Bis dahin bleiben Ihre Einstellungen gespeichert.",
    summaryOn: "An, für: {keywords}",
    summaryOff: "Aus",
    keywords: "Stichwörter",
    keywordsHint: "Ein Wort oder eine kurze Wendung; drücken Sie nach jedem Enter. Bis zu 20.",
    keywordInput: "Neues Stichwort",
    addKeyword: "Hinzufügen",
    removeKeyword: "„{keyword}“ entfernen",
    replyText: "Nachricht per Direct",
    replyHint: "Bis zu 1000 Zeichen. Die Kundin oder der Kunde kann antworten, und der Assistent führt das Gespräch weiter.",
    save: "Speichern",
    saving: "Wird gespeichert…",
    savedToast: "Antworten auf Kommentare sind gespeichert",
    errors: {
      keywordsMissing: "Fügen Sie mindestens ein Stichwort hinzu",
      replyMissing: "Schreiben Sie die Nachricht",
      keyword: "Bis zu 50 Zeichen, in einer Zeile",
      tooMany: "Höchstens 20 Stichwörter",
    },
  },
  tunnel: {
    title: "WhatsApp, Instagram und Messenger",
    text: "Verbinden Sie sie jetzt mit Ihrem Facebook-Konto oder später auf der Seite „Kanäle“.",
    connect: "{channel} verbinden",
    connected: "Verbunden",
  },
};
