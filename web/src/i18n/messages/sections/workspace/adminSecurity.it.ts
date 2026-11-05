/** `adminSecurity.*` texts of the platform admin's Encryption keys page, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminSecurityEn } from "./adminSecurity.en";

export const adminSecurityIt: Translation<typeof adminSecurityEn> = {
  nav: "Chiavi di cifratura",
  title: "Chiavi di cifratura",
  description: "Le chiavi che cifrano i token dei canali e dei calendari, e lo spostamento di ogni token salvato sulla chiave più recente.",
  ring: {
    title: "Mazzo di chiavi",
    keyCount: "Chiavi nel mazzo",
    single: "Una sola chiave cifra e decifra tutto. Per cambiarla, metti una nuova chiave per prima in ENCRYPTION_KEYS, fai il deploy, poi ricifra da qui.",
    several: {
      one: "La prima chiave cifra tutto ciò che è nuovo; {count} chiave più vecchia decifra solo ciò che ha cifrato. Ricifra, poi rimuovila come indica il runbook.",
      other: "La prima chiave cifra tutto ciò che è nuovo; {count} chiavi più vecchie decifrano solo ciò che hanno cifrato. Ricifra, poi rimuovile come indica il runbook.",
    },
  },
  run: {
    title: "Ricifratura",
    description: "Ogni token di canale e di calendario viene cifrato di nuovo con la chiave più recente, e i webhook di Telegram vengono registrati di nuovo con il suo segreto.",
    start: "Ricifra i token salvati",
    confirmTitle: "Ricifrare tutti i token salvati?",
    confirmBody:
      "Il worker in background cifra di nuovo ogni token di canale e di calendario con la chiave più recente e registra di nuovo i webhook di Telegram. I clienti non notano nulla. L'esecuzione viene annotata nel registro di audit.",
    confirm: "Ricifra",
    starting: "Avvio…",
    started: "Ricifratura in coda",
    alreadyRunning: "Una ricifratura è già in corso.",
    none: "Ancora nessuna ricifratura",
    noneDescription: "Avviala dopo aver messo una nuova chiave per prima in ENCRYPTION_KEYS. Con una sola chiave verifica soltanto che ogni token si decifri.",
    status: {
      queued: "In coda",
      running: "In corso",
      done: "Completata",
      failed: "Non riuscita",
    },
    facts: {
      requested: "Richiesta",
      started: "Avviata",
      finished: "Terminata",
      keys: "Chiavi nel mazzo in quel momento",
      total: "Token verificati",
      current: "Già sulla chiave più recente",
      rotated: "Cifrati di nuovo",
      unreadable: "Impossibili da decifrare",
      webhooksRenewed: "Webhook di Telegram registrati di nuovo",
      webhooksFailed: "Webhook di Telegram non registrati",
    },
    verdict: {
      working: "Il worker sta ricifrando. Questa pagina si aggiorna da sola.",
      clean: "Ogni token salvato è cifrato con la chiave più recente. Le chiavi più vecchie si possono rimuovere quando i link delle notifiche e le registrazioni delle chiamate che hanno cifrato sono scaduti (vedi il runbook).",
      cleanSingle: "Ogni token salvato si decifra con l'unica chiave del mazzo.",
      unreadable: {
        one: "{count} token non si decifra con nessuna chiave: il titolare deve ricollegare quel canale.",
        other: "{count} token non si decifrano con nessuna chiave: i titolari devono ricollegare quei canali.",
      },
      webhooks: {
        one: "{count} webhook di Telegram non è stato registrato di nuovo: ricifra più tardi.",
        other: "{count} webhook di Telegram non sono stati registrati di nuovo: ricifra più tardi.",
      },
      failed: "L'esecuzione si è fermata: {error}. Avviala di nuovo; i token già spostati restano spostati.",
      keysChanged: {
        one: "Il mazzo di chiavi è cambiato dopo questa esecuzione ({then} chiave allora, {now} adesso): ricifra di nuovo.",
        other: "Il mazzo di chiavi è cambiato dopo questa esecuzione ({then} chiavi allora, {now} adesso): ricifra di nuovo.",
      },
    },
  },
};
