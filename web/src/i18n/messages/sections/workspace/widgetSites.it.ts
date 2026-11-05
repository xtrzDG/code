/** `widgetSites.*` texts of Channels → Website chat → the websites allowed to show the chat, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { widgetSitesEn } from "./widgetSites.en";

export const widgetSitesIt: Translation<typeof widgetSitesEn> = {
  title: "Siti web che possono mostrare la chat",
  description:
    "Il codice della chat funziona su qualsiasi sito in cui viene incollato. Elenca i tuoi siti e la chat funzionerà solo lì, così nessuno potrà usare il tuo assistente, e il tuo piano, da una copia del codice.",
  anySite: "Qualsiasi sito",
  sites: { one: "{count} sito", other: "{count} siti" },
  listLabel: "Siti consentiti",
  empty: "Ancora nessun elenco: la chat funziona su qualsiasi sito.",
  addFieldLabel: "Indirizzo del sito",
  addHint: "Come nella barra degli indirizzi del browser. L'indirizzo con www. e quelli con http o https contano come lo stesso sito.",
  placeholder: "https://trattoria-milano.it",
  add: "Aggiungi",
  remove: "Rimuovi {site}",
  invalid: "Questo non è l'indirizzo di un sito. Scrivilo come nella barra degli indirizzi del browser, ad esempio trattoria-milano.it.",
  duplicate: "Questo sito è già nell'elenco.",
  full: { one: "L'elenco può contenere fino a {count} sito.", other: "L'elenco può contenere fino a {count} siti." },
  alwaysAllowed: "La tua pagina della chat e l'anteprima in questo pannello funzionano sempre.",
  ownerOnly: "Solo un titolare può modificare questo elenco.",
  save: "Salva l'elenco",
  saving: "Salvataggio…",
  unsaved: "Non salvato",
  savedToast: "Elenco dei siti salvato",
  clearedToast: "La chat funziona di nuovo su qualsiasi sito",
};
