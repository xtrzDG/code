/** `adminIncident.*` texts of "Record incident" on the platform admin's System page, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminIncidentEn } from "./adminIncident.en";

export const adminIncidentIt: Translation<typeof adminIncidentEn> = {
  title: "Registra incidente",
  description:
    "Ogni attività coinvolta riceve una voce nel suo registro di audit. Una violazione dei dati personali invia anche l'avviso del punto 12.1 del DPA a tutti i titolari di quelle attività.",
  kind: "Tipo di incidente",
  severity: "Gravità",
  severityHint: "SEV1: la maggior parte dei clienti non riceve risposte, oppure i dati sono usciti dalla piattaforma. SEV2: un canale o una funzione non va per molti. SEV3: poche attività, oppure esiste una soluzione alternativa.",
  severityBreach: "Una violazione dei dati personali è sempre SEV1.",
  name: "Titolo",
  nameHint: "Una riga per il registro, senza nomi di clienti.",
  startedAt: "Inizio",
  detectedAt: "Rilevato",
  detectedHint: "Quando la piattaforma se n'è accorta; vuoto per adesso. Per una violazione, le 48 ore per l'avviso decorrono da qui.",
  timeZone: "Gli orari sono nel fuso orario del tuo dispositivo.",
  businesses: "Attività coinvolte",
  businessesHint: "ID delle attività (business_…) o link alle loro pagine in Clienti, uno per riga.",
  scope: {
    legend: "Quali attività",
    listed: "Le attività elencate qui sotto",
    all: "Tutte le attività della piattaforma",
    allHint:
      "Viene registrato subito; poi il worker passa tutte le attività a gruppi: ognuna riceve la sua voce di audit e, in caso di violazione, i titolari ricevono l'avviso. Il registro mostra a che punto è arrivato.",
  },
  announcement: {
    offer: "Pubblica anche un avviso di stato",
    offerHint: "Da ora compare sulla pagina di stato pubblica e nel banner di ogni pannello; risolvilo da questa pagina quando l'incidente è finito.",
    title: "Avviso di stato",
  },
  breach: {
    title: "Avviso ai titolari",
    description:
      "I titolari lo ricevono via e-mail, o via SMS se non hanno un indirizzo, nella lingua del loro pannello. L'inglese è obbligatorio; aggiungi georgiano e russo così ogni titolare lo legge nella sua lingua.",
    subjects: "Persone coinvolte (circa)",
    records: "Dati coinvolti (circa)",
    language: "Lingua dell'avviso",
    complete: "completo",
    partial: "incompleto",
    fields: {
      nature: "Cosa è successo",
      subject_categories: "Categorie di persone",
      record_categories: "Categorie di dati",
      likely_consequences: "Conseguenze probabili",
      measures: "Misure adottate o proposte",
    },
  },
  submit: "Registra incidente",
  submitBreach: "Registra e avvisa i titolari",
  saving: "Registrazione…",
  errors: {
    required: "Compila questo campo.",
    title: "Scrivi da 3 a 160 caratteri.",
    future: "Questo orario è nel futuro.",
    order: "Il rilevamento non può precedere l'inizio.",
    businessIds: "Non è un ID di attività: {tokens}",
    tooManyBusinesses: "Al massimo 1.000 attività.",
    count: "Un numero intero da 0 a 1.000.000.000.",
    noticeRequired: "L'avviso in inglese è obbligatorio.",
    noticeIncomplete: "Compila tutti e cinque i testi di questa lingua, oppure nessuno.",
  },
};
