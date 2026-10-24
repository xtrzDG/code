/** `notifications.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { notificationsEn } from "./notifications.en";

export const notificationsDe: Translation<typeof notificationsEn> = {
  device: {
    title: "Auf diesem Gerät",
    description: "Übergaben, Anfragen und Buchungen kommen als Benachrichtigungen auf diesem Telefon oder Computer an, auch wenn das Dashboard geschlossen ist.",
    on: "An",
    off: "Aus",
    enable: "Benachrichtigungen auf diesem Gerät einschalten",
    disable: "Auf diesem Gerät ausschalten",
    test: "Test senden",
    enabled: "Benachrichtigungen sind auf diesem Gerät an",
    disabled: "Benachrichtigungen sind auf diesem Gerät aus",
    unsupported:
      "Dieser Browser kann keine Benachrichtigungen anzeigen. Fügen Sie das Dashboard auf iPhone oder iPad zum Home-Bildschirm hinzu („Teilen“ → „Zum Home-Bildschirm“) und öffnen Sie es von dort.",
    denied: "Benachrichtigungen sind für diese Website blockiert. Erlauben Sie sie in den Website-Einstellungen des Browsers und versuchen Sie es erneut.",
    notConfigured: "Benachrichtigungen auf Geräten sind auf diesem Server noch nicht eingerichtet.",
    dismissed: "Benachrichtigungen wurden nicht erlaubt. Drücken Sie die Schaltfläche erneut, wenn Sie bereit sind.",
    failed: "Benachrichtigungen konnten in diesem Browser nicht eingeschaltet werden. Versuchen Sie es erneut.",
    lastDelivered: "Letzte Benachrichtigung {time}",
    neverDelivered: "Noch keine Benachrichtigungen",
    lastError: "Die letzte ist nicht angekommen: {error}",
    otherDevices: "Meine anderen Geräte",
    otherDevice: "Gerät hinzugefügt {date}",
    removeOther: "Ausschalten",
    removeOtherLabel: "Benachrichtigungen auf dem am {date} hinzugefügten Gerät ausschalten",
    removed: "Benachrichtigungen sind auf diesem Gerät aus",
    testDelivered: "Die Testbenachrichtigung ist unterwegs zu diesem Gerät",
    testFailed: "Der Test hat dieses Gerät nicht erreicht: {error}",
    testPending: "Der Test an dieses Gerät wird erneut versucht: {error}",
  },
  setupReminders: {
    title: "Einrichtungserinnerungen",
    label: "Einrichtungserinnerungen",
    description:
      "Einige kurze Erinnerungen in den ersten Tagen, in Telegram, per E-Mail und auf Ihren Geräten: wenn der Assistent noch nicht live ist, nur einen Kanal oder noch keine Kunden hat. Sie hören von selbst auf, sobald alles erledigt ist.",
  },
  mine: {
    title: "Was mich erreicht",
    description: "Ihre Wahl für Ihre eigenen Geräte in diesem Unternehmen. Zeiten in der Zeitzone des Unternehmens, {timeZone}.",
    eventOff: "Sie bekommen keine Benachrichtigungen mehr zu: {event}",
  },
  preferences: {
    events: "Benachrichtigen über",
    noEvents: "Nichts ausgewählt: Es kommen keine Benachrichtigungen.",
    event: {
      handoff: "Kunden, die eine Person brauchen",
      lead: "Neue Anfragen",
      booking: "Buchungen: neue, verschobene und stornierte",
    },
    quietHours: "Ruhezeiten",
    quietHoursHint: "Benachrichtigungen warten, bis die Ruhezeiten enden. Dringende Übergaben kommen trotzdem an.",
    quietHoursToggle: "Benachrichtigungen in diesen Stunden zurückhalten",
    quietFrom: "Von",
    quietUntil: "Bis",
    errors: {
      format: "Geben Sie eine Uhrzeit wie 22:00 ein",
      same: "Beginn und Ende müssen sich unterscheiden",
    },
    summary: {
      everything: "Alles, jederzeit",
      events: "Nur: {events}",
      nothing: "Nichts",
      quiet: "Ruhe {from}–{until}",
    },
    short: {
      handoff: "Übergaben",
      lead: "Anfragen",
      booking: "Buchungen",
    },
  },
  contacts: {
    test: "Test senden",
    testLabel: "Testbenachrichtigung an {name} senden",
    testDelivered: "Der Test hat {name} erreicht",
    testSimulated: "Hier gibt es keinen Anbieter: Der Test an {name} wurde ins Server-Log geschrieben",
    testFailed: "Der Test an {name} ist nicht angekommen: {error}",
    testPending: "Der Test an {name} wird erneut versucht: {error}",
    providerMissing: "Auf dem Server nicht eingerichtet",
    providerMissingHint: "Auf diesem Weg wird nichts gesendet, bis der {channel}-Anbieter der Plattform konfiguriert ist.",
    testUnavailable: "Ein Test kann nicht gesendet werden: {channel} ist auf dem Server der Plattform nicht eingerichtet.",
    status: {
      delivered: "Zugestellt",
      pending: "Wartet",
      dead: "Nicht zugestellt",
    },
    deliveredAt: "Zugestellt {time}",
    attemptedAt: "Versucht {time}",
    never: "Noch nichts gesendet",
    telegramLinked: "Verknüpft als @{username}",
    telegramChat: "Telegram-Chat",
  },
  link: {
    expiredTitle: "Dieser Link ist abgelaufen",
    expiredDescription: "Benachrichtigungslinks funktionieren 7 Tage. Öffnen Sie das Unternehmen, um zu finden, worum es in der Benachrichtigung ging.",
    invalidTitle: "Dieser Link funktioniert nicht",
    invalidDescription: "Er ist vielleicht abgeschnitten oder für ein anderes Konto gedacht. Melden Sie sich mit dem Konto an, an das die Benachrichtigung ging.",
    openBusiness: "Unternehmen öffnen",
    toBusinesses: "Meine Unternehmen",
  },
};
