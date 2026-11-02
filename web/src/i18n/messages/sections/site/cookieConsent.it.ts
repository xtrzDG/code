/** `cookieConsent.*`: il banner dei cookie del sito pubblico, il modo per riaprirlo dal piè di pagina e la pagina dell'informativa (/[locale]/cookies), italiano. */

import type { Translation } from "../../../translate";
import type { cookieConsentEn } from "./cookieConsent.en";

export const cookieConsentIt: Translation<typeof cookieConsentEn> = {
  title: "Cookie su questo sito",
  text: "Usiamo i cookie necessari al funzionamento del sito. Con il tuo consenso ricordiamo anche quale pagina o link ti ha portato qui la prima volta, per sapere da dove arrivano le attività che si registrano. Non usiamo cookie pubblicitari né di tracciamento di terze parti. Puoi cambiare la tua scelta in qualsiasi momento da “Impostazioni cookie” in fondo alla pagina.",
  statementLink: "Leggi l'informativa sui cookie",
  accept: "Accetta",
  reject: "Rifiuta",
  close: "Chiudi e continua senza accettare",
  failed: "Non è stato possibile salvare la tua scelta. Riprova.",
  settings: "Impostazioni cookie",
  nav: "Informativa sui cookie",
  description: "Quali cookie usano il sito e l'area riservata della piattaforma, a cosa serve ciascuno, quanto dura e come dare o revocare il consenso.",
};
