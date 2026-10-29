/** `quickReplies.*` texts of Settings → Quick replies, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { quickRepliesEn } from "./quickReplies.en";

export const quickRepliesIt: Translation<typeof quickRepliesEn> = {
  description:
    "Le risposte che il tuo team invia spesso, pronte in ogni lingua della tua attività. In una conversazione digita / per inserirne una: il nome del cliente e la prenotazione si compilano da soli.",
  add: "Nuova risposta rapida",
  loading: "Caricamento delle risposte rapide…",
  emptyTitle: "Ancora nessuna risposta rapida",
  emptyDescription: "Orari di apertura, indicazioni stradali, “La richiamiamo noi”: scrivile una volta e inviale con due tocchi.",
  listLabel: "Risposte rapide",
  languages: "Lingue",
  variablesUsed: "Compila in automatico",
  edit: "Modifica",
  editLabel: "Modifica la risposta rapida “{title}”",
  delete: "Elimina",
  deleteLabel: "Elimina la risposta rapida “{title}”",
  confirmDelete: {
    title: "Eliminare questa risposta rapida?",
    description: "“{title}” scompare dalla selezione per tutto il team.",
    confirm: "Elimina",
  },
  deleted: "Risposta rapida eliminata",
  saved: "Risposta rapida salvata",
  editor: {
    newTitle: "Nuova risposta rapida",
    editTitle: "Modifica la risposta rapida",
    description: "Scrivila in ogni lingua usata dai tuoi clienti. Il personale vede il testo nella lingua della conversazione.",
    title: "Nome",
    titleHint: "Ciò che il team vede nella selezione.",
    shortcut: "Scorciatoia",
    shortcutHint: "Si digita dopo / nel campo di risposta: lettere, cifre, - e _.",
    shortcutInvalid: "Usa solo lettere, cifre, - e _, senza spazi.",
    texts: "Testo",
    textIn: "Testo in {language}",
    textHint: "Lascia vuota una lingua se non ti serve. È richiesto almeno un testo.",
    needOneText: "Scrivi il testo in almeno una lingua.",
    insert: "Inserisci",
    insertLabel: "Inserisci {variable} nel testo in {language}",
    preview: "Anteprima",
    sample: {
      name: "Giulia",
      bookingTime: "sab, 19:30",
    },
    save: "Salva",
    saving: "Salvataggio…",
    cancel: "Annulla",
    length: "{count} / {max}",
  },
  variables: {
    name: "Nome del cliente",
    booking_time: "Orario della prenotazione",
    business_name: "Nome dell'attività",
  },
  errors: {
    shortcut_taken: "Un'altra risposta rapida usa già questa scorciatoia.",
    too_many_quick_replies: "Un'attività può avere al massimo 100 risposte rapide. Eliminane una che non usi più.",
    unknown_variable: "Si possono compilare solo {name}, {booking_time} e {business_name}. Controlla le parentesi graffe nel testo.",
    duplicate_language: "Ogni lingua può avere un solo testo.",
  },
};
