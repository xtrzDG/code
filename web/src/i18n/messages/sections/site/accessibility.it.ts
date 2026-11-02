/** `accessibility.*`: la dichiarazione di accessibilità (/[locale]/accessibility), italiano. */

import type { Translation } from "../../../translate";
import type { accessibilityEn } from "./accessibility.en";

export const accessibilityIt: Translation<typeof accessibilityEn> = {
  nav: "Accessibilità",
  description:
    "Quanto sono accessibili il sito della piattaforma, le pagine di chat e di prenotazione delle attività e l'area riservata dei titolari, cosa non lo è ancora e come segnalare un problema.",
  title: "Dichiarazione di accessibilità",
  lead: "{operator} vuole che tutti, comprese le persone con disabilità, possano usare il suo servizio. Questa dichiarazione riguarda questo sito, le pagine di chat e la chat per siti web delle attività, le pagine di prenotazione degli ospiti e l'area riservata dei titolari.",
  operatorFallback: "Il fornitore di questo servizio",
  basis:
    "Segue il modello pubblicato da AgID (Agenzia per l'Italia Digitale) e i requisiti di accessibilità dell'Atto europeo sull'accessibilità (Direttiva (UE) 2019/882) e della Legge 4/2004.",
  statusTitle: "Stato di conformità",
  statusText:
    "Il servizio è parzialmente conforme alle Linee guida per l'accessibilità dei contenuti web (WCAG) 2.2 al livello AA, il livello a cui rimanda la norma europea EN 301 549. Parzialmente conforme significa che alcune parti non soddisfano ancora del tutto questi requisiti; quelle che conosciamo sono elencate qui sotto.",
  limitationsTitle: "Contenuti non ancora accessibili",
  limitations: {
    legalLanguage:
      "I testi legali (termini di servizio, informativa privacy, informativa sui cookie e accordo sul trattamento dei dati) sono pubblicati solo in inglese; le versioni italiane sono in preparazione.",
    userContent:
      "Le foto e i file che le attività o i loro clienti inviano in una conversazione, e i testi che le attività scrivono da sé, possono non avere una descrizione testuale o una struttura chiara: non possiamo controllare tutto ciò che pubblicano.",
    thirdParty:
      "Le pagine di altri servizi a cui la piattaforma rimanda non rientrano in questa dichiarazione: la verifica anti-bot all'accesso (Cloudflare Turnstile), le pagine di pagamento (Flitt, Stripe) e i siti web delle attività.",
    audit:
      "Non è ancora stata svolta una verifica manuale completa con tecnologie assistive (come i lettori di schermo), quindi possono restare barriere che i controlli automatici non trovano.",
  },
  methodTitle: "Come è stata redatta questa dichiarazione",
  methodText:
    "Si basa su una valutazione effettuata dal fornitore stesso, non su una verifica di un esperto indipendente. Lo strumento axe-core controlla automaticamente le pagine pubbliche, la pagina di chat, la chat per siti web, la pagina di prenotazione e le pagine dell'area riservata secondo le sue regole WCAG 2.0, 2.1 e 2.2 ai livelli A e AA (le pagine pubbliche e quelle dell'area riservata sia con il tema chiaro sia con quello scuro). Gli strumenti automatici trovano solo una parte dei possibili problemi.",
  dateText: "Questa dichiarazione è stata redatta il {date} e viene rivista almeno una volta all'anno e ogni volta che il servizio cambia in modo significativo.",
  feedbackTitle: "Feedback e recapiti",
  feedbackText:
    "Se incontri una barriera, o ti serve qualcosa del servizio in un altro formato, indicaci la pagina e cosa non ha funzionato. Rispondiamo entro 30 giorni.",
  feedbackEmail: "Scrivi a {email}.",
  feedbackContact: "Usa i recapiti della pagina Contatti.",
  contactLink: "Contatti",
  enforcementTitle: "Procedura di attuazione",
  enforcementText:
    "Se la nostra risposta non ti soddisfa, o non l'hai ricevuta entro 30 giorni, puoi segnalarlo ad AgID (Agenzia per l'Italia Digitale), l'autorità che vigila sull'accessibilità digitale in Italia, tramite il suo modulo online.",
  enforcementLink: "Segnala ad AgID (form.agid.gov.it)",
  technologiesTitle: "Tecnologie utilizzate",
  technologiesText:
    "Il servizio si basa su HTML, CSS, JavaScript e WAI-ARIA ed è pensato per Chrome, Edge, Firefox e Safari aggiornati, su computer e telefono.",
};
