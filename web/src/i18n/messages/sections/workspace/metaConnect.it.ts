/** `metaConnect.*` texts of "Continue with Facebook" for WhatsApp, Instagram and Messenger, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { metaConnectEn } from "./metaConnect.en";

export const metaConnectIt: Translation<typeof metaConnectEn> = {
  continue: "Continua con Facebook",
  intro: {
    whatsapp:
      "Accedi con Facebook, poi scegli o crea il tuo account WhatsApp Business e il numero nella finestra di Facebook. Al collegamento del numero pensiamo noi.",
    instagram:
      "Accedi con Facebook e scegli la pagina a cui è collegato il tuo account professionale Instagram. Al collegamento pensiamo noi.",
    messenger: "Accedi con Facebook e scegli la pagina: l'assistente risponderà alle sue chat di Messenger.",
  },
  orManual: "Hai già gli ID e la chiave? Puoi comunque inserirli a mano.",
  preparing: "Preparazione di Facebook…",
  starting: "Avvio…",
  openWindow: "Apri la finestra di Facebook",
  openHint: "Il browser ci ha chiesto di attendere un clic: l'accesso a Facebook si apre in una nuova finestra.",
  waiting: "Completa la procedura nella finestra di Facebook. Questa finestra resta in attesa.",
  finishing: "Collegamento…",
  notices: {
    cancelled: "La finestra di Facebook si è chiusa prima della fine. Riprova quando vuoi.",
    failed: "Facebook non è riuscito a completare la registrazione. Riprova o inserisci i dati manualmente.",
    unavailable:
      "L'accesso a Facebook non si è caricato (potrebbe bloccarlo un ad blocker o un'estensione per la privacy). Riprova più tardi o inserisci i dati manualmente.",
  },
  pages: {
    title: "Scegli una pagina",
    hint: "Le pagine che gestisci su Facebook.",
    instagramHint: "Solo una pagina collegata a un account professionale Instagram può collegare Instagram.",
    none: "Facebook non mostra pagine gestite da te. Ricomincia e seleziona la pagina della tua attività nella finestra di Facebook.",
    instagram: "Instagram: @{username}",
    instagramNoName: "Account Instagram collegato",
    noInstagram: "Nessun account Instagram collegato",
    connect: "Collega questa pagina",
    connecting: "Collegamento…",
  },
  refusals: {
    meta_link_expired: "Questo accesso a Facebook è terminato. Ricomincia.",
    meta_not_configured: "L'accesso con Facebook non è configurato su questo server. Inserisci i dati manualmente.",
    meta_permission_missing:
      "Facebook non ha concesso tutte le autorizzazioni necessarie. Ricomincia e lascia selezionate tutte le caselle.",
    whatsapp_account_missing:
      "Facebook non ha restituito alcun account WhatsApp Business. Ricomincia e scegline o creane uno.",
    whatsapp_number_missing: "Quell'account WhatsApp Business non ha ancora un numero di telefono. Aggiungine uno nella finestra di Facebook.",
    whatsapp_pin_mismatch:
      "Questo numero ha la verifica in due passaggi con un altro PIN. Disattivala in WhatsApp Manager, poi riprova.",
    meta_page_not_found: "Facebook non ha dato accesso a questa pagina. Ricomincia e selezionala nella finestra di Facebook.",
    instagram_account_missing:
      "Questa pagina non ha un account professionale Instagram collegato. Collegane uno nelle impostazioni di Instagram o scegli un'altra pagina.",
  },
  commentReplies: {
    title: "Risposte ai commenti",
    toggle: "Rispondi in Direct ai commenti con una parola chiave",
    description:
      "Quando qualcuno scrive una delle tue parole chiave in un commento sotto un post, l'assistente gli invia un messaggio in Direct. Al massimo uno al giorno per persona e 60 all'ora.",
    unavailable: "Le risposte ai commenti partiranno con il prossimo aggiornamento del servizio. Fino ad allora le tue impostazioni restano salvate.",
    summaryOn: "Attive, per: {keywords}",
    summaryOff: "Disattivate",
    keywords: "Parole chiave",
    keywordsHint: "Una parola o una breve frase; premi Invio dopo ognuna. Fino a 20.",
    keywordInput: "Nuova parola chiave",
    addKeyword: "Aggiungi",
    removeKeyword: "Rimuovi “{keyword}”",
    replyText: "Messaggio in Direct",
    replyHint: "Fino a 1000 caratteri. Il cliente può rispondere e l'assistente prosegue la conversazione.",
    save: "Salva",
    saving: "Salvataggio…",
    savedToast: "Le risposte ai commenti sono salvate",
    errors: {
      keywordsMissing: "Aggiungi almeno una parola chiave",
      replyMissing: "Scrivi il messaggio",
      keyword: "Fino a 50 caratteri, su una sola riga",
      tooMany: "Fino a 20 parole chiave",
    },
  },
  tunnel: {
    title: "WhatsApp, Instagram e Messenger",
    text: "Collegali ora con il tuo account Facebook, oppure più tardi nella pagina Canali.",
    connect: "Collega {channel}",
    connected: "Collegato",
  },
};
