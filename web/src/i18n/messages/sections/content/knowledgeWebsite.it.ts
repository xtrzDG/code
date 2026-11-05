/** `knowledgeWebsite.*` in Italian: importing from the website (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { knowledgeWebsiteEn } from "./knowledgeWebsite.en";

export const knowledgeWebsiteIt: Translation<typeof knowledgeWebsiteEn> = {
  website: {
    tabsLabel: "Cosa importare",
    tabMenu: "Menù o listino prezzi",
    tabWebsite: "Dal tuo sito",
    title: "Importa dal tuo sito",
    description:
      "Indica l'indirizzo del tuo sito. Leggiamo fino a 15 pagine (menù, prezzi, servizi, domande e orari di apertura) e ti mostriamo cosa abbiamo trovato prima che cambi qualcosa.",
    address: "Indirizzo del sito",
    addressHint: "Il tuo sito, per esempio https://la-mia-trattoria.it",
    start: "Leggi il mio sito",
    starting: "Avvio…",
    safety: "Vengono lette solo le pagine pubbliche. Nulla arriva ai clienti finché non verifichi le voci e le aggiungi.",
    progressLabel: "Lettura del tuo sito",
    queued: "Avvio tra un attimo…",
    opening: "Apertura di {host}…",
    reading: "Lettura della pagina {current} di {total}",
    found: { one: "Finora trovata {count} voce", other: "Finora trovate {count} voci" },
    leaveHint: "Puoi lasciare questa pagina: l'importazione continua e ciò che trova ti aspetta qui.",
    doneTitle: { one: "Trovata {count} voce sul tuo sito", other: "Trovate {count} voci sul tuo sito" },
    doneDescription: {
      one: "{count} pagina letta. Controlla le voci prima che vengano aggiunte.",
      other: "{count} pagine lette. Controlla le voci prima che vengano aggiunte.",
    },
    review: "Controlla cosa è stato trovato",
    waitingTitle: "Le voci del tuo sito ti aspettano",
    waitingDescription: { one: "{count} voce trovata su {host}.", other: "{count} voci trovate su {host}." },
    nothingTitle: "Non è stato trovato nulla da importare",
    nothingDescription:
      "Nelle pagine non c'erano menù, prezzi, servizi, domande o orari di apertura leggibili. Prova un altro indirizzo o aggiungi le voci a mano.",
    another: "Prova un altro indirizzo",
    sourcePage: "Da {page}",
    errors: {
      required: "Inserisci l'indirizzo del tuo sito",
      address: "Inserisci un indirizzo web come https://la-mia-trattoria.it",
      failedTitle: "Impossibile leggere il sito",
      notPublic: "Questo non è un sito pubblico. Usa l'indirizzo che i clienti aprono nel browser.",
      notHttp: "Usa un indirizzo web che inizia con http:// o https://.",
      port: "Gli indirizzi con una porta come :8080 non si possono leggere. Usa l'indirizzo abituale del tuo sito.",
      credentials: "Rimuovi nome utente e password dall'indirizzo.",
      unknownHost: "Nessun sito trovato a questo indirizzo. Controlla che sia scritto bene.",
      timeout: "Il sito ha impiegato troppo a rispondere. Riprova tra qualche minuto.",
      unreachable: "Impossibile aprire il sito. Controlla l'indirizzo e che il sito sia online.",
      httpStatus: "Il sito ha risposto con l'errore {status}. Controlla l'indirizzo.",
      unreadable: "L'indirizzo si è aperto, ma non come una pagina web che possiamo leggere (è un file o è troppo grande). Prova l'indirizzo della tua home page.",
      reader: "Il servizio di lettura non è disponibile in questo momento. Riprova più tardi.",
      interrupted: "L'importazione si è interrotta prima di finire. Avviala di nuovo.",
      running: "Il tuo sito è già in lettura. Attendi che quell'importazione finisca.",
      tooMany: "Il tuo sito è stato importato 10 volte nell'ultima ora. Riprova più tardi.",
    },
  },
};
