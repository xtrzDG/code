/** `mfa.*` in German: two-factor sign-in (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { mfaEn } from "./mfa.en";

export const mfaDe: Translation<typeof mfaEn> = {
  secondStep: {
    title: "Zwei-Faktor-Anmeldung",
    description: "Öffnen Sie Ihre Authenticator-App und geben Sie den 6-stelligen Code ein, den sie für Assistant Workshop anzeigt.",
    code: "Code aus der App",
    recoveryDescription: "Geben Sie einen Ihrer gespeicherten Wiederherstellungscodes ein. Jeder Code funktioniert einmal.",
    recoveryCode: "Wiederherstellungscode",
    recoveryHint: "12 Buchstaben und Ziffern, zum Beispiel {example}",
    useRecovery: "Stattdessen einen Wiederherstellungscode verwenden",
    useApp: "Die Authenticator-App verwenden",
    verify: "Anmelden",
    verifying: "Wird geprüft…",
    startOver: "Erneut anmelden",
  },
  enrollment: {
    title: "Zwei-Faktor-Anmeldung einrichten",
    description:
      "Plattform-Admins melden sich zusätzlich mit einem Code aus einer Authenticator-App an. Richten Sie jetzt eine ein: Es dauert eine Minute, und die nächsten Anmeldungen fragen nur nach dem Code.",
    start: "Jetzt einrichten",
    starting: "Wird vorbereitet…",
  },
  setup: {
    title: "Authenticator-App einrichten",
    stepInstall: "Installieren Sie eine Authenticator-App auf Ihrem Telefon: Google Authenticator, Microsoft Authenticator, 1Password oder eine andere.",
    stepScan: "Scannen Sie diesen QR-Code mit der App oder geben Sie den Schlüssel ein.",
    stepCode: "Geben Sie den 6-stelligen Code ein, den die App anzeigt.",
    qrLabel: "QR-Code für die Authenticator-App",
    key: "Schlüssel",
    copyKey: "Schlüssel kopieren",
    code: "Code aus der App",
    confirm: "Einschalten",
    confirming: "Wird eingeschaltet…",
  },
  recovery: {
    title: "Speichern Sie Ihre Wiederherstellungscodes",
    description:
      "Wenn Sie Ihr Telefon verlieren, melden Sie sich mit einem dieser Codes statt mit der App an. Jeder Code funktioniert einmal. Sie werden nur jetzt angezeigt: Bewahren Sie sie in einem Passwortmanager auf oder drucken Sie sie aus.",
    copy: "Kopieren",
    download: "Herunterladen",
    fileHeading: "Wiederherstellungscodes von Assistant Workshop für {account}. Jeder Code funktioniert einmal.",
    saved: "Ich habe die Codes sicher aufbewahrt",
    continue: "Weiter",
  },
  stepUp: {
    title: "Bestätigen Sie, dass Sie es sind",
    description: "Diese Aktion braucht eine frische Bestätigung.",
    totp: "Geben Sie den Code aus Ihrer Authenticator-App ein.",
    loginCode: "Wir haben einen Code an {destination} gesendet. Geben Sie ihn hier ein.",
    sending: "Code wird gesendet…",
    code: "Code",
    confirm: "Bestätigen",
    confirming: "Wird geprüft…",
    resend: "Neuen Code senden",
    confirmed: "Bestätigt. Wird jetzt ausgeführt.",
  },
  errors: {
    wrongCode: "Der Code ist falsch oder wurde schon verwendet. Versuchen Sie den neuesten Code.",
    expired: "Diese Anmeldung ist abgelaufen. Beginnen Sie neu.",
    tooManyAttempts: "Zu viele falsche Codes. Melden Sie sich erneut an.",
    codeFormat: "Geben Sie die 6 Ziffern ein",
  },
};
