/** `knowledge.aliases.*` auf Deutsch: die Namen eines Eintrags in den anderen Sprachen des Unternehmens. */

import type { Translation } from "../../../translate";
import type { knowledgeAliasesEn } from "./knowledgeAliases.en";

export const knowledgeAliasesDe: Translation<typeof knowledgeAliasesEn> = {
  aliases: {
    title: "Namen in anderen Sprachen",
    hint: "Kunden fragen in ihrer eigenen Sprache. Diese Namen werden wie der Titel gesucht, und die von Ihnen bestätigten werden zu Einstiegsfragen im Website-Chat.",
    listLabel: "Namen auf {language}",
    none: "Noch kein Name auf {language}",
    suggested: "Vorschlag",
    suggestedHint: "Vorgeschlagene Namen werden schon gesucht, Kunden sehen sie aber erst, wenn Sie sie bestätigen.",
    accept: "„{text}“ bestätigen",
    remove: "„{text}“ entfernen",
    addLabel: "Namen auf {language} hinzufügen",
    placeholder: "Name auf {language}",
    add: "Hinzufügen",
    tooLong: "Ein Name darf höchstens 200 Zeichen haben",
    duplicate: "Dieser Name steht schon in der Liste",
    tooMany: "Höchstens drei Namen pro Sprache",
    suggest: "Übersetzungen vorschlagen",
    suggesting: "Vorschläge werden gesucht…",
    saveTitleFirst: "Speichern Sie zuerst den neuen Titel und fragen Sie dann nach Übersetzungen.",
    suggestedCount: {
      one: "{count} Name vorgeschlagen: Prüfen Sie ihn unten",
      other: "{count} Namen vorgeschlagen: Prüfen Sie sie unten",
    },
    nothingSuggested: "Nichts Neues vorzuschlagen: Jede Sprache hat schon einen Namen.",
  },
};
