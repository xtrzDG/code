/** `knowledge.aliases.*` in Italian: an item's names in the business's other languages (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { knowledgeAliasesEn } from "./knowledgeAliases.en";

export const knowledgeAliasesIt: Translation<typeof knowledgeAliasesEn> = {
  aliases: {
    title: "Nomi in altre lingue",
    hint: "I clienti chiedono nella propria lingua. Questi nomi vengono cercati come il titolo e quelli che approvi diventano domande iniziali della chat del tuo sito.",
    listLabel: "Nomi in {language}",
    none: "Ancora nessun nome in {language}",
    suggested: "Suggeriti",
    suggestedHint: "I nomi suggeriti vengono già cercati, ma i clienti li vedono solo dopo che li hai accettati.",
    accept: "Accetta “{text}”",
    remove: "Rimuovi “{text}”",
    addLabel: "Aggiungi un nome in {language}",
    placeholder: "Nome in {language}",
    add: "Aggiungi",
    tooLong: "Un nome può avere al massimo 200 caratteri",
    duplicate: "Questo nome è già nell'elenco",
    tooMany: "Al massimo tre nomi per lingua",
    suggest: "Suggerisci traduzioni",
    suggesting: "Ricerca di suggerimenti…",
    saveTitleFirst: "Salva prima il nuovo titolo, poi chiedi le traduzioni.",
    suggestedCount: {
      one: "{count} nome suggerito: controllalo qui sotto",
      other: "{count} nomi suggeriti: controllali qui sotto",
    },
    nothingSuggested: "Niente di nuovo da suggerire: ogni lingua ha già un nome.",
  },
};
