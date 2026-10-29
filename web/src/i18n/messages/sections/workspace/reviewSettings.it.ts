/** `reviewSettings.*` texts of Settings → Reviews, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { reviewSettingsEn } from "./reviewSettings.en";

export const reviewSettingsIt: Translation<typeof reviewSettingsEn> = {
  description: "Chiedi ai clienti com'è andata la loro visita, invita tutti a recensirti su Google e guarda cosa hanno risposto.",
  stats: {
    title: "Ultimi 30 giorni",
    description: "I clienti a cui abbiamo chiesto della visita e cosa hanno risposto.",
    asked: "Contattati",
    answered: "Hanno risposto",
    answeredShare: "{percent} dei contattati",
    average: "Valutazione media",
    averageValue: "{score} su 5",
    noAverage: "Ancora nessuna valutazione",
    opened: "Hanno aperto il link per la recensione",
    notTracked: "Non conteggiato su questa piattaforma",
    scores: "Valutazioni",
    scoreRow: { one: "{score} stella: {count}", other: "{score} stelle: {count}" },
    notAsked: "Non contattati: {count}",
    notDelivered: "Non consegnati: {count}",
  },
  feedback: {
    title: "Feedback dopo le visite",
    description:
      "Dopo una visita completata chiediamo al cliente di valutarla da 1 a 5, nell'app di messaggistica che ha usato e nella sua lingua. La piattaforma risponde da sola alla valutazione: ringrazia il cliente e gli invia il tuo link per la recensione.",
    toggle: "Chiedi ai clienti com'è andata la visita",
    turnedOff: "Ai clienti non viene più chiesto della loro visita",
    delay: "Quando chiedere",
    delayHint: "Calcolato dalla fine della prenotazione.",
    delayMinutes: { one: "{count} minuto dopo la visita", other: "{count} minuti dopo la visita" },
    delayHours: { one: "{count} ora dopo la visita", other: "{count} ore dopo la visita" },
    delayDays: { one: "{count} giorno dopo la visita", other: "{count} giorni dopo la visita" },
    template: "Nome del modello WhatsApp",
    templateHint:
      "Per i clienti WhatsApp che non scrivono da 24 ore: il modello di utilità approvato sul tuo numero (lettere latine minuscole, cifre e trattini bassi).",
    templateInvalid: "Usa solo lettere latine minuscole, cifre e trattini bassi.",
    readiness: {
      off: "Le richieste di feedback sono disattivate.",
      everywhere: "Chiediamo ai clienti su Telegram, WhatsApp, Messenger e Instagram; i clienti WhatsApp che non scrivono da un giorno ricevono il tuo modello.",
      window: "Chiediamo ai clienti entro 24 ore dal loro ultimo messaggio; i clienti WhatsApp che non scrivono da più tempo vengono saltati finché non imposti il modello.",
    },
    whatsappMissing: "WhatsApp non è collegato.",
    connectWhatsapp: "Collega WhatsApp",
    rules:
      "Per ogni visita chiediamo una sola volta, e a ogni cliente al massimo una volta al giorno. I clienti che hanno risposto STOP non ricevono richieste. Una valutazione di 3 o meno finisce anche in Conversazioni → Serve una persona, così qualcuno si fa sentire.",
  },
  link: {
    title: "Link per le recensioni Google",
    description:
      "Chiunque risponda riceve questo link insieme al ringraziamento, qualunque sia la sua valutazione: invitare solo i clienti soddisfatti è contro le regole di Google.",
    label: "Link alla tua pagina delle recensioni Google",
    hint: "Nel Profilo dell'attività su Google scegli “Chiedi recensioni” e copia il link.",
    invalid: "Inserisci un link completo che inizi con https://",
    tracked: "Lo inviamo tramite l'indirizzo breve della piattaforma per contare quanti clienti lo aprono.",
    missing: "Senza link, i clienti ricevono solo un ringraziamento.",
  },
  template: {
    title: "Testo del modello",
    description:
      "Crea in Meta Business Manager un modello WhatsApp di utilità con questo testo, con una traduzione per ogni lingua; il suo unico parametro è il nome della tua attività. I clienti lo ricevono nella loro lingua, oppure in inglese se manca la traduzione.",
    body: "Testo per il modello",
    example: "Cosa leggono i clienti",
  },
  requests: {
    title: "Ultime richieste",
    description: "Le ultime 20 visite per cui abbiamo chiesto un feedback e cosa hanno risposto i clienti.",
    empty: "Ancora nessuna richiesta",
    emptyDescription: "Quando il feedback è attivo, chiediamo ai clienti un parere dopo le loro visite.",
    customer: "Cliente",
    visitEnded: "Visita terminata il {time}",
    rating: "Valutazione: {score} su 5",
    openedLink: "Ha aperto il link per la recensione",
    openConversation: "Apri la conversazione",
    notAskedBecause: "Non richiesto: {reason}",
    statuses: {
      sent: "In attesa di risposta",
      answered: "Risposto",
      skipped: "Non richiesto",
      failed: "Non consegnato",
    },
    skipReasons: {
      opted_out: "il cliente ha risposto STOP",
      no_contact: "i dati del cliente sono stati cancellati",
      no_channel: "nessuna app di messaggistica a cui scrivere",
      window_closed: "dopo 24 ore WhatsApp richiede il modello approvato",
      already_asked: "già richiesto oggi",
      daily_limit: "è stato raggiunto il limite giornaliero di messaggi",
    },
  },
};
