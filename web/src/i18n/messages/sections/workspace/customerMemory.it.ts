/** `customerMemory.*` texts of Settings → General's customer memory card, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { customerMemoryEn } from "./customerMemory.en";

export const customerMemoryIt: Translation<typeof customerMemoryEn> = {
  title: "Memoria dei clienti",
  description:
    "L'assistente riconosce i clienti che tornano: li saluta, conosce le loro prossime prenotazioni e le richieste aperte e ricorda di cosa parlavano le conversazioni precedenti.",
  remember: {
    label: "Ricorda i clienti che tornano",
    hint: "Due ore dopo che una conversazione si è fermata, ne viene salvato un breve riepilogo. Se la disattivi, non viene scritto alcun riepilogo e ogni conversazione riparte da zero.",
  },
  notes: {
    label: "Condividi le note del team con l'assistente",
    hint: "Le note interne sulle ultime conversazioni del cliente entrano nella memoria. L'assistente non le cita mai al cliente.",
    needsMemory: "Prima attiva la memoria dei clienti.",
  },
  remembers: {
    title: "Cosa ricorda l'assistente",
    visits: "Quanto spesso il cliente ha scritto e quando è passato l'ultima volta",
    summaries: "Di cosa parlavano le sue tre conversazioni più recenti",
    bookings: "Le sue prossime prenotazioni e le richieste che il tuo team non ha ancora chiuso",
  },
  bookingsQuestion:
    "Su qualsiasi canale i clienti possono anche chiedere “A che ora è la mia prenotazione?”: l'assistente cerca le prenotazioni di chi lo chiede.",
  privacy:
    "La memoria non passa mai a un'altra attività. Se cancelli i dati di un cliente in Impostazioni → Privacy, si cancella anche ciò che l'assistente ricordava di lui.",
  ownerOnly: "Solo i titolari possono modificarlo.",
  turnedOn: "L'assistente ricorda i clienti che tornano",
  turnedOff: "La memoria dei clienti è disattivata",
  notesShared: "Ora l'assistente legge le note del team",
  notesHidden: "Le note del team restano al team",
};
