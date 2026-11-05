/** `reports.*` in Italian: Overview → Reports (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { reportsEn } from "./reports.en";

export const reportsIt: Translation<typeof reportsEn> = {
  description: "Cosa ha fatto l'assistente ogni mese e ogni settimana, e i riepiloghi che ricevi.",
  loading: "Caricamento dei report…",
  opened: "Dal tuo riepilogo",
  past: "Report precedenti",
  kindLabel: "Tipo di report",
  kinds: {
    monthly: "Mensile",
    weekly: "Settimanale",
    daily: "Giornaliero",
  },
  empty: {
    title: "Ancora nessun report",
    monthly: "Il primo report mensile viene creato il 1° del mese e riguarda il mese precedente.",
    weekly: "I riepiloghi settimanali vengono creati il lunedì e riguardano la settimana precedente.",
    daily: "I riepiloghi giornalieri vengono creati ogni mattina per i titolari che li hanno attivati.",
  },
  monthSoFar: {
    title: "Questo mese finora",
    next: "Il report completo arriva il {date}",
  },
  summary: {
    bookings: { one: "{count} prenotazione", other: "{count} prenotazioni" },
    requests: { one: "{count} richiesta", other: "{count} richieste" },
  },
  delivery: {
    sent: { one: "Inviato a {count} titolare", other: "Inviato a {count} titolari" },
    quiet: "Non inviato: periodo senza attività",
    noRecipients: "Nessuno lo aveva attivato",
  },
  details: {
    toggle: "Tutti i numeri",
    caption: "I numeri del report a confronto con il periodo precedente",
    measure: "Cosa",
    change: "Variazione",
    before: "prima: {value}",
    noCheck: "Non era impostato uno scontrino medio, quindi il report non contiene una stima in denaro.",
    ownerCheck: "Importi stimati con il tuo scontrino medio di {money}.",
    typicalCheck: "Importi stimati con lo scontrino medio tipico di {money} per il tuo tipo di attività.",
    bookedPrices: "Importi calcolati dai prezzi di ciò che è stato prenotato.",
    mixedCheck: "Importi calcolati dai prezzi di ciò che è stato prenotato; le prenotazioni senza prezzo valgono lo scontrino medio di {money}.",
  },
  rows: {
    assistantBookings: "Prenotazioni dell'assistente",
    estimate: "Valore (stima)",
    staffTime: "Tempo del personale risparmiato",
    afterHours: "Conversazioni fuori orario",
    conversations: "Conversazioni",
    customerMessages: "Messaggi dei clienti",
    assistantReplies: "Risposte dell'assistente",
    calls: "Chiamate gestite",
    bookings: "Tutte le prenotazioni",
    requests: "Richieste",
    handoffs: "Passate a una persona",
  },
  duration: {
    hoursMinutes: "{hours} h {minutes} min",
    minutes: "{minutes} min",
  },
  digests: {
    title: "I tuoi riepiloghi",
    description: "Cosa ha fatto l'assistente, inviato a te nella tua lingua con un link per tornare qui.",
    monthly: "Report mensile",
    monthlyHint: "Il 1° del mese alle 9:00, sul mese precedente",
    weekly: "Riepilogo settimanale",
    weeklyHint: "Il lunedì alle 9:00, sulla settimana precedente",
    daily: "Riepilogo giornaliero",
    dailyHint: "Ogni mattina alle 9:00, sul giorno precedente",
  },
};
