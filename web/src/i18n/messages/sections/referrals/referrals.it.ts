/** `referrals.*` in Italian: inviting a business (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { referralsEn } from "./referrals.en";

export const referralsIt: Translation<typeof referralsEn> = {
  title: "Invita un’attività: un mese gratis",
  lead: "Condividi il tuo link con un’attività che conosci. Quando paga la sua prima fattura, ricevete entrambi un mese gratis del vostro piano.",
  terms: "Il mese arriva come credito sulle tue prossime fatture. Le altre attività di cui sei titolare non contano.",
  menu: "Invita un’attività",
  menuHint: "Un mese gratis per entrambi",
  linkLabel: "Il tuo link di invito",
  copy: "Copia il link",
  share: "Condividi",
  shareText: "Rispondiamo ai nostri clienti con {app}. Iscriviti con il mio link e riceviamo entrambi un mese gratis:",
  showQr: "Mostra il codice QR",
  hideQr: "Nascondi il codice QR",
  qrLabel: "Codice QR del tuo link di invito",
  noLink: "Il tuo link di invito non è ancora pronto. Riprova più tardi.",
  loading: "Caricamento del tuo invito…",
  statsLabel: "I tuoi inviti",
  invited: "Iscritti",
  paid: "Hanno pagato",
  rewarded: "Mesi guadagnati",
  close: "Chiudi",
  poweredBy: {
    title: "Link “Powered by”",
    description: "Un piccolo link con il tuo codice di invito sotto la chat, sulla pagina della chat e sul cartoncino stampato.",
    toggle: "Mostra il link “Powered by”",
    plusOnly: "Toglierlo è incluso nel piano Plus.",
    hidden: "Disattivato: la chat, la pagina e il cartoncino non mostrano alcun link.",
    saved: "Salvato",
    footer: "Powered by {app}",
  },
  partnerPortal: "Area partner",
};
