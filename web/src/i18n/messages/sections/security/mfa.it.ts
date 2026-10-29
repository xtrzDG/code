/** `mfa.*` texts of two-factor sign-in, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { mfaEn } from "./mfa.en";

export const mfaIt: Translation<typeof mfaEn> = {
  secondStep: {
    title: "Accesso con verifica in due passaggi",
    description:
      "Apri la tua app di autenticazione e inserisci il codice a 6 cifre che mostra per Assistant Workshop.",
    code: "Codice dall'app",
    recoveryDescription:
      "Inserisci uno dei codici di recupero che hai salvato. Ogni codice funziona una sola volta.",
    recoveryCode: "Codice di recupero",
    recoveryHint: "12 lettere e cifre, ad esempio {example}",
    useRecovery: "Usa invece un codice di recupero",
    useApp: "Usa l'app di autenticazione",
    verify: "Accedi",
    verifying: "Verifica…",
    startOver: "Accedi di nuovo",
  },
  enrollment: {
    title: "Configura la verifica in due passaggi",
    description:
      "Anche gli amministratori della piattaforma accedono con un codice da un'app di autenticazione. Configurala ora: ci vuole un minuto, e ai prossimi accessi ti verrà chiesto solo il codice.",
    start: "Configura ora",
    starting: "Preparazione…",
  },
  setup: {
    title: "Configura un'app di autenticazione",
    stepInstall:
      "Installa un'app di autenticazione sul telefono: Google Authenticator, Microsoft Authenticator, 1Password o un'altra.",
    stepScan: "Scansiona questo codice QR con l'app oppure inserisci la chiave.",
    stepCode: "Inserisci il codice a 6 cifre mostrato dall'app.",
    qrLabel: "Codice QR per l'app di autenticazione",
    key: "Chiave",
    copyKey: "Copia la chiave",
    code: "Codice dall'app",
    confirm: "Attiva",
    confirming: "Attivazione…",
  },
  recovery: {
    title: "Salva i tuoi codici di recupero",
    description:
      "Se perdi il telefono, accedi con uno di questi codici al posto dell'app. Ogni codice funziona una sola volta. Vengono mostrati solo adesso: conservali in un gestore di password o stampali.",
    copy: "Copia",
    download: "Scarica",
    fileHeading:
      "Codici di recupero di Assistant Workshop per {account}. Ogni codice funziona una sola volta.",
    saved: "Ho salvato i codici in un posto sicuro",
    continue: "Continua",
  },
  stepUp: {
    title: "Conferma che sei tu",
    description: "Questa azione richiede una nuova conferma.",
    totp: "Inserisci il codice della tua app di autenticazione.",
    loginCode: "Abbiamo inviato un codice a {destination}. Inseriscilo qui.",
    sending: "Invio del codice…",
    code: "Codice",
    confirm: "Conferma",
    confirming: "Verifica…",
    resend: "Invia un nuovo codice",
    confirmed: "Confermato. Procediamo.",
  },
  errors: {
    wrongCode: "Il codice è errato o è già stato usato. Prova con il codice più recente.",
    expired: "Questo accesso è scaduto. Ricomincia.",
    tooManyAttempts: "Troppi codici errati. Accedi di nuovo.",
    codeFormat: "Inserisci le 6 cifre",
  },
};
