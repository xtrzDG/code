/** `handoffs.*` in Italian: conversations that need a person (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { handoffsEn } from "./handoffs.en";

export const handoffsIt: Translation<typeof handoffsEn> = {
  urgency: {
    critical: "Critica",
    high: "Urgente",
    normal: "Normale",
    low: "Bassa",
  },
  reason: {
    customer_request: "Ha chiesto una persona",
    complaint: "Reclamo",
    vip_guest: "Ospite VIP",
    non_standard_request: "Richiesta particolare",
    unknown_answer: "L'assistente non conosceva la risposta",
    emergency: "Emergenza",
    sensitive_topic: "Argomento delicato",
    profile_rule: "Una delle tue regole",
    unverified_numbers: "Prezzi o cifre non confermati",
  },
  status: {
    pending: "Notifica al personale in corso",
    notified: "Personale avvisato",
    notification_failed: "Notifica non riuscita",
    resolved: "Risolto",
  },
  notificationFailedHint: "Il personale non ha ricevuto la notifica. Richiama il cliente e controlla i contatti nelle impostazioni.",
  summaryCodes: {
    model_declined: "L'assistente non ha voluto rispondere a questo messaggio.",
    model_unavailable: "L'assistente non è stato disponibile per qualche istante e non ha potuto rispondere.",
    answer_unfinished: "L'assistente non è riuscito a completare la risposta.",
    unverified_values: "L'assistente non ha inviato una risposta con cifre o affermazioni che non risultano nei dati della tua attività.",
    call_booking_unverified_values:
      "Durante la chiamata l'assistente ha citato cifre che non risultano nei dati della tua attività. Confronta la prenotazione nata da questa chiamata con la trascrizione.",
    call_request_unverified_values:
      "Durante la chiamata l'assistente ha citato cifre che non risultano nei dati della tua attività. Confronta la richiesta nata da questa chiamata con la trascrizione.",
    reply_undelivered: "La risposta dell'assistente non è arrivata al cliente. Contattalo in un altro modo.",
    data_erased: "Dati cancellati su richiesta del cliente.",
  },
  summaryCodesWithValues: {
    unverified_values:
      "L'assistente non ha inviato una risposta con cifre o affermazioni che non risultano nei dati della tua attività ({values}).",
    call_booking_unverified_values:
      "Durante la chiamata l'assistente ha citato cifre che non risultano nei dati della tua attività ({values}). Confronta la prenotazione nata da questa chiamata con la trascrizione.",
    call_request_unverified_values:
      "Durante la chiamata l'assistente ha citato cifre che non risultano nei dati della tua attività ({values}). Confronta la richiesta nata da questa chiamata con la trascrizione.",
  },
  quote: {
    customer: "Il messaggio del cliente",
    reply: "La risposta non arrivata",
  },
};
