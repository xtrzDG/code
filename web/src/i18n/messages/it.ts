import type { Messages } from "../translate";
import { insightsIt } from "./sections/insights";
import { contentIt } from "./sections/content";
import { workspaceIt } from "./sections/workspace";
import { shellIt } from "./sections/shell";
import { setupFlowIt } from "./sections/setup";
import { assistantFlowIt } from "./sections/assistant";
import { securityFlowIt } from "./sections/security";
import { helpIt } from "./sections/help";
import { siteIt } from "./sections/site";
import { customersSectionIt } from "./sections/customers";
import { brandsSectionIt } from "./sections/brands";
import { referralsSectionIt } from "./sections/referrals";
import { growthSectionIt } from "./sections/growth";
import { nichesSectionIt } from "./sections/niches";
import { onboardingIt } from "./onboarding/it";
import { landingIt } from "./landing/it";

/**
 * Italian texts (italiano, informal "tu" for the owner), drafted by the team
 * and awaiting a native speaker's review (config.ts, NEEDS_REVIEW_LOCALES).
 * Keys as in en.ts.
 */
export const it: Messages = {
  common: {
    appName: "Assistant Workshop",
    tagline: "Il tuo assistente AI per il front office",
    save: "Salva",
    saving: "Salvataggio…",
    saved: "Salvato",
    cancel: "Annulla",
    close: "Chiudi",
    retry: "Riprova",
    loading: "Caricamento…",
    edit: "Modifica",
    delete: "Elimina",
    done: "Fatto",
    yes: "Sì",
    no: "No",
    optional: "facoltativo",
    select: "Seleziona…",
    search: "Cerca",
    requestId: "ID richiesta: {id}",
    typeToConfirm: "Digita {text} per confermare",
    undo: "Annulla",
  },
  language: {
    label: "Lingua dell’interfaccia",
  },
  theme: {
    label: "Tema",
    dark: "Scuro",
    light: "Chiaro",
    system: "Sistema",
  },
  nav: {
    mainNavigation: "Navigazione principale",
    skipToContent: "Vai al contenuto",
    allBusinesses: "Tutte le attività",
    bookings: "Prenotazioni",
    knowledge: "Conoscenze",
    channels: "Canali",
    admin: "Piattaforma",
  },
  shell: {
    switchBusiness: "Cambia attività",
    signedInAs: "Accesso effettuato come {name}",
    signOut: "Esci",
    signingOut: "Uscita…",
    platformAdmin: "Amministratore della piattaforma",
  },
  auth: {
    aboutLink: "Cosa fa l’assistente →",
    title: "Accedi",
    subtitle: "Inserisci il tuo numero di telefono o la tua e-mail e ti invieremo un codice. Sei nuovo? L’account viene creato automaticamente.",
    methodLabel: "Accedi con",
    methodPhone: "Telefono",
    methodEmail: "E-mail",
    country: "Paese",
    phone: "Numero di telefono",
    phonePlaceholder: "Numero senza prefisso internazionale",
    phoneHint: "Va bene qualsiasi formato: con o senza +{code}.",
    email: "E-mail",
    emailPlaceholder: "you@example.com",
    sendCode: "Ricevi un codice",
    sendingCode: "Invio…",
    codeTitle: "Inserisci il codice",
    codeSentTo: {
      email: "Abbiamo inviato un codice di 6 cifre a {destination} via e-mail.",
      sms: "Abbiamo inviato un codice di 6 cifre a {destination} via SMS.",
      whatsapp: "Abbiamo inviato un codice di 6 cifre a {destination} su WhatsApp.",
      telegram: "Abbiamo inviato un codice di 6 cifre a {destination} su Telegram.",
    },
    code: "Codice",
    codeHint: "Il codice è valido per {minutes} min.",
    verify: "Accedi",
    verifying: "Verifica…",
    resendIn: "Puoi chiedere un nuovo codice tra {seconds} s",
    resend: "Invia un nuovo codice",
    codeResent: "Un nuovo codice è in arrivo",
    sendByChannelInstead: "Nessun codice? Invialo via {channel}",
    changeDestination: "Usa un altro numero o un’altra e-mail",
    sessionExpired: "La sessione è scaduta. Accedi di nuovo.",
    countryUnavailable: "non ancora disponibile",
    botCheck: {
      title: "Ancora un passaggio",
      hint: "Conferma di non essere un robot e ti invieremo subito il codice.",
      failed: "La verifica non è riuscita. Riprova.",
      unavailable: "Impossibile caricare la verifica. Controlla la connessione o disattiva i blocchi dei contenuti, poi ricarica la pagina.",
    },
    deliveryChannels: {
      sms: "SMS",
      whatsapp: "WhatsApp",
      telegram: "Telegram",
      email: "e-mail",
    },
    errors: {
      phoneRequired: "Inserisci il tuo numero di telefono",
      phoneInvalid: "Questo non sembra un numero di telefono",
      emailInvalid: "Inserisci un indirizzo e-mail valido",
      codeInvalid: "Inserisci le 6 cifre del messaggio",
      wrongCode: "Il codice è sbagliato o scaduto. Controllalo o chiedine uno nuovo.",
      tooManyAttempts: "Troppi tentativi. Attendi un po’ e chiedi un nuovo codice.",
      resendTooSoon: "Ti abbiamo appena inviato un codice. Attendi 30 secondi prima di chiederne un altro.",
      countryRestricted: "La registrazione non è ancora disponibile in questo paese. Puoi accedere con l’e-mail.",
      cannotReceive: "Questo numero non può ricevere codici. Usa un numero di cellulare o accedi con l’e-mail.",
    },
  },
  businesses: {
    title: "Le tue attività",
    subtitle: "Ogni attività ha il suo assistente, il suo profilo e i suoi canali.",
    emptyTitle: "Ancora nessuna attività",
    emptyDescription: "Crea la tua prima attività: scegli un settore e un paese, al resto pensiamo noi.",
    name: "Nome dell’attività",
    role: {
      owner: "Titolare",
      staff: "Personale",
      agency: "Agenzia",
    },
    status: {
      onboarding: "Profilo in compilazione",
      testing: "In prova",
      live: "Online",
      paused: "In pausa",
    },
  },
  pages: {
    bookings: { description: "Le prenotazioni con il loro stato; aggiungine una a mano." },
    knowledge: { description: "Menù, servizi, prezzi e risposte; le domande dei clienti rimaste senza risposta." },
    channels: { description: "App di messaggistica, inoltro di chiamata e chat del sito web." },
    billing: { description: "Piano, consumo del pacchetto, fatture e pagamento." },
    admin: { title: "Piattaforma", description: "Tutti i clienti, il loro stato, i consumi e il margine." },
  },
  ...onboardingIt,
  ...landingIt,
  errors: {
    title: "Qualcosa è andato storto",
    description: "Riprova. Se continua a succedere, inviaci l’ID della richiesta.",
    notFoundTitle: "Pagina non trovata",
    notFoundDescription: "La pagina non esiste o non hai accesso.",
    backHome: "Alle mie attività",
    twoFactorRequired:
      "Un’attività qui chiede al suo team di accedere con un’app di autenticazione. Configurane una in Account → Sicurezza, accedi di nuovo e riprova.",
    codes: {
      not_found: "Non trovato, oppure non hai accesso.",
      validation_failed: "Controlla i dati inseriti.",
      conflict: "Questo è in conflitto con lo stato attuale. Aggiorna la pagina e riprova.",
      authentication_required: "Accedi di nuovo.",
      access_denied: "Non hai l’autorizzazione per questa azione.",
      rate_limited: "Troppi tentativi. Attendi un po’ e riprova.",
      payload_too_large: "È troppo grande per essere inviato. Scegli un file più piccolo o accorcia il testo.",
      external_service_error: "Un servizio esterno non risponde. Riprova tra un minuto.",
      internal_error: "Errore del server. Ne siamo già al corrente.",
      backend_unavailable: "Il server non è raggiungibile. Controlla la connessione e riprova.",
      network_error: "Nessuna connessione. Controlla internet e riprova.",
      forbidden_origin: "La richiesta è stata bloccata per motivi di sicurezza. Ricarica la pagina.",
      unknown_error: "Qualcosa è andato storto. Riprova.",
    },
  },
  validation: {
    required: "Compila questo campo",
    url: "Inserisci un link completo che inizi con https://",
    number: "Inserisci un numero",
    positive: "Inserisci un numero maggiore di zero",
    wholeNumber: "Inserisci un numero intero",
    durationRange: "Inserisci da 5 a 720 minuti",
    time: "Inserisci l’ora nel formato HH:MM",
    tooLong: "Il testo è troppo lungo",
    hoursOverlap: "Gli intervalli di questo giorno si sovrappongono",
  },
  ...insightsIt,
  ...contentIt,
  ...workspaceIt,
  ...shellIt,
  ...setupFlowIt,
  ...assistantFlowIt,
  ...securityFlowIt,
  ...helpIt,
  ...siteIt,
  ...customersSectionIt,
  ...referralsSectionIt,
  ...brandsSectionIt,
  ...growthSectionIt,
  ...nichesSectionIt,
};
