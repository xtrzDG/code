/** `waitlist.*` in Italian: Bookings → Waitlist (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { waitlistEn } from "./waitlist.en";

export const waitlistIt: Translation<typeof waitlistEn> = {
  loading: "Caricamento della lista d’attesa…",
  filters: {
    label: "Quali iscrizioni",
    active: "In attesa",
    booked: "Prenotati",
    ended: "Concluse",
  },
  empty: {
    active: "Nessuno è in attesa",
    activeDescription:
      "Quando una giornata è al completo, l’assistente propone al cliente di entrare in lista d’attesa. Un posto liberato da una cancellazione o da uno spostamento viene offerto al primo a cui va bene.",
    booked: "Ancora nessuna prenotazione dalla lista d’attesa",
    bookedDescription: "Qui compaiono, con la loro prenotazione, i clienti che hanno accettato un posto liberato.",
    ended: "Ancora niente di concluso",
    endedDescription: "Un’iscrizione si conclude quando il cliente rifiuta, non risponde in tempo o la giornata è passata.",
  },
  customer: "Cliente",
  wants: "Vorrebbe il {date}",
  window: {
    any: "a qualsiasi ora",
    between: "{from}–{to}",
    from: "dalle {from}",
    until: "fino alle {to}",
  },
  nights: { one: "{count} notte", other: "{count} notti" },
  status: {
    waiting: "In attesa",
    offered: "Posto tenuto",
    booked: "Prenotato",
    expired: "Conclusa",
  },
  endReasons: {
    declined: "Ha rifiutato il posto",
    no_answer: "Non ha risposto in tempo",
    date_passed: "La giornata è passata",
    unreachable: "Non è stato possibile contattarlo",
    removed: "Tolto dalla lista",
  },
  offer: {
    held: "Tenuto per lui: {place}, {time}",
    heldNoPlace: "Tenuto per lui: {time}",
    until: "Fino alle {time}",
    minutesLeft: { one: "Manca {count} minuto", other: "Mancano {count} minuti" },
    answerDue: "In attesa di risposta",
  },
  offerCount: { one: "Posto offerto {count} volta", other: "Posto offerto {count} volte" },
  joined: "Iscritto {time}",
  booked: "Prenotato {time}",
  ended: "Conclusa {time}",
  openConversation: "Apri la conversazione",
  remove: "Togli dalla lista",
  removeTitle: "Togliere {name} dalla lista d’attesa?",
  removeBody: "Non gli verrà offerto un posto liberato. Un posto tenuto per lui in questo momento passa al successivo in lista.",
  removeConfirm: "Togli dalla lista",
  removed: "Tolto dalla lista d’attesa",
  timeZone: "Gli orari sono nel fuso {timezone}.",
  settings: {
    title: "Impostazioni lista d’attesa",
    description:
      "Una prenotazione annullata o spostata libera un posto: viene tenuto per il primo cliente a cui va bene e offerto sul suo canale e nella sua lingua. Con un “sì” viene prenotato.",
    toggle: "Usa la lista d’attesa",
    off: "L’assistente non propone la lista d’attesa. I clienti già in lista ci restano fino alla loro giornata.",
    hold: "Tieni un posto liberato per",
    holdHint: "Se non arriva una risposta entro questo tempo, il posto passa al successivo in lista.",
    holdOption: { one: "{count} minuto", other: "{count} minuti" },
    save: "Salva",
    saved: "Impostazioni della lista d’attesa salvate",
    ownersOnly: "Solo un titolare può modificare queste impostazioni.",
  },
};
