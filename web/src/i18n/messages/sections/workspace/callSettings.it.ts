/** `callSettings.*` texts of Settings → Calls, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { callSettingsEn } from "./callSettings.en";

export const callSettingsIt: Translation<typeof callSettingsEn> = {
  description: "Cosa succede dopo ogni chiamata: un riepilogo per il tuo personale e un messaggio a chi ha chiamato senza ricevere risposta.",
  summaries: {
    title: "Riepiloghi delle chiamate",
    description:
      "Dopo ogni chiamata, le chat del personale su Telegram e WhatsApp ricevono chi ha chiamato, cosa voleva, come si è conclusa la chiamata e tutto ciò che l'assistente ha detto e che non si trova nei tuoi dati. Le chiamate rimaste senza risposta vengono segnalate su ogni canale, così qualcuno richiama.",
    toggle: "Invia un riepilogo dopo ogni chiamata",
    contactsHint: "Chi li riceve: i contatti del personale in Impostazioni → Notifiche.",
    openContacts: "Contatti del personale",
    turnedOff: "I riepiloghi delle chiamate sono disattivati",
  },
  textBack: {
    title: "Messaggio dopo una chiamata persa",
    description:
      "Quando chi chiama non riesce a parlare con nessuno (la linea è occupata, nessuno risponde, riaggancia presto, l'assistente non può prendere la chiamata o nessuno risponde a un trasferimento), gli scriviamo entro un paio di minuti, nella sua lingua. La sua risposta prosegue come conversazione WhatsApp in Conversazioni.",
    toggle: "Scrivi a chi ha chiamato senza ricevere risposta",
    template: "Nome del modello WhatsApp",
    templateHint: "Il nome del modello di utilità approvato sul tuo numero WhatsApp: lettere latine minuscole, cifre e trattini bassi.",
    templateInvalid: "Usa solo lettere latine minuscole, cifre e trattini bassi.",
    sms: "Invia un SMS quando WhatsApp non è possibile",
    smsHint: "Dal mittente SMS della piattaforma, quando il numero non ha WhatsApp o il modello viene rifiutato.",
    smsNeedsTextBack: "Prima attiva i messaggi a chi ha chiamato senza ricevere risposta.",
    rules: "Ogni chiamante riceve al massimo un messaggio al giorno. Non scriviamo ai clienti che hanno scelto di non ricevere messaggi o che ti stanno già scrivendo.",
    turnedOff: "I messaggi a chi ha chiamato senza ricevere risposta sono disattivati",
    smsTurnedOff: "Gli SMS a chi ha chiamato senza ricevere risposta sono disattivati",
    readiness: {
      whatsapp: "Chi chiama riceve il tuo modello WhatsApp.",
      sms: "Chi chiama riceve un SMS.",
      none: "Non si può ancora inviare nulla: collega WhatsApp e indica il nome del modello, oppure consenti gli SMS.",
      off: "I messaggi dopo le chiamate perse sono disattivati.",
    },
    whatsappMissing: "WhatsApp non è collegato.",
    connectWhatsapp: "Collega WhatsApp",
    smsMissing: "Gli SMS non sono configurati su questa piattaforma.",
  },
  template: {
    title: "Testo del modello",
    description:
      "Crea in Meta Business Manager un modello WhatsApp di utilità con questo testo, con una traduzione per ogni lingua; il suo unico parametro è il nome della tua attività. Chi chiama lo riceve nella sua lingua, oppure in inglese se manca la traduzione.",
    body: "Testo per il modello",
  },
  history: {
    title: "Ultimi messaggi dopo le chiamate perse",
    description: "Gli ultimi 20 chiamanti che non hanno ricevuto risposta e cosa è stato inviato loro.",
    empty: "Ancora nessuna chiamata persa",
    emptyDescription: "Qui compariranno i chiamanti che non ricevono risposta.",
    hiddenNumber: "Numero privato",
    openConversation: "Apri la conversazione",
    notSentBecause: "Non inviato: {reason}",
    statuses: {
      queued: "In invio",
      sent: "Inviato",
      failed: "Non consegnato",
      skipped: "Non inviato",
    },
    channels: {
      whatsapp: "WhatsApp",
      sms: "SMS",
    },
    reasons: {
      no_answer: "Nessuna risposta",
      busy: "Linea occupata",
      abandoned: "Ha riagganciato prima della risposta",
      line_failed: "Chiamata non connessa",
      not_started: "L'assistente non ha potuto prendere la chiamata",
      no_speech: "Ha riagganciato senza parlare",
      transfer_unanswered: "Trasferimento senza risposta",
      callback_requested: "Ha chiesto di essere richiamato",
    },
    skipReasons: {
      turned_off: "i messaggi dopo le chiamate perse erano disattivati",
      opted_out: "il cliente ha scelto di non ricevere messaggi",
      already_texted: "ha già ricevuto un messaggio oggi",
      daily_limit: "è stato raggiunto il limite giornaliero",
      in_conversation: "ti sta già scrivendo",
      no_channel: "nessun canale da cui inviare",
      not_live: "l'assistente non era online",
      no_caller_number: "il numero era privato",
      too_late: "la chiamata è stata segnalata troppo tardi",
    },
  },
};
