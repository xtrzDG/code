/** `nichePage.*` texts of the public page for one kind of business, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { nichePageEn } from "./nichePage.en";

export const nichePageIt: Translation<typeof nichePageEn> = {
  metaTitle: "{niche}: un assistente AI per chiamate e messaggi",
  metaDescription: "{description} L'assistente risponde giorno e notte nelle lingue dei tuoi clienti, prende prenotazioni e richieste e passa i casi complessi al tuo team.",
  breadcrumb: "Settori",
  eyebrow: "Un assistente AI per questo settore",
  title: "{niche}: risposta a ogni chiamata e messaggio",
  lead: "L'assistente sa cosa chiedono di solito i clienti di questo settore, risponde in base ai tuoi prezzi e alle tue regole e non si inventa nulla.",
  primary: "Crea un assistente",
  secondary: "Prova la demo",
  doesTitle: "Cosa fa qui l'assistente",
  books: "Prenota: {resource}, in base ai tuoi orari e ai posti liberi",
  noBookings: "Raccoglie ordini e richieste con i dettagli che servono al tuo team",
  answers: "Risponde a domande su prezzi, orari e regole nella lingua del cliente",
  handoff: "Passa reclami e richieste insolite a una persona con un breve riepilogo",
  sensitive: "Le domande delicate (salute, sicurezza, questioni legali) vanno sempre a una persona: l'assistente non dà consigli in merito",
  integrationsTitle: "Funziona con",
  plansTitle: "I piani adatti",
  plansText: "Le attività come questa di solito iniziano con {plans}. Ogni piano include una prova gratuita.",
  pricingLink: "Vedi i prezzi",
  demoTitle: "Parla con un assistente demo",
  demoText: "Un'attività demo di questo settore risponde come una vera; nessuna prenotazione viene registrata davvero.",
  otherTitle: "Altri settori",
  notFound: "Questo settore non esiste.",
};
