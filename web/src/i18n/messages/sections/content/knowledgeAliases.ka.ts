/** `knowledge.aliases.*` ქართულად: ჩანაწერის სახელები ბიზნესის სხვა ენებზე, ჩიპები ცოდნის რედაქტორში. */

import type { Translation } from "../../../translate";
import type { knowledgeAliasesEn } from "./knowledgeAliases.en";

export const knowledgeAliasesKa: Translation<typeof knowledgeAliasesEn> = {
  aliases: {
    title: "სახელები სხვა ენებზე",
    hint: "მომხმარებლები საკუთარ ენაზე კითხულობენ. ეს სახელები სათაურის მსგავსად მოიძებნება, თქვენ მიერ დამტკიცებული კი საიტის ჩატის მზა კითხვებად იქცევა.",
    listLabel: "სახელები: {language}",
    none: "სახელი ({language}) ჯერ არ არის",
    suggested: "შემოთავაზებული",
    suggestedHint:
      "შემოთავაზებული სახელები უკვე მოიძებნება, მაგრამ მომხმარებლები მათ მხოლოდ თქვენი დამტკიცების შემდეგ ნახავენ.",
    accept: "დაამტკიცეთ „{text}“",
    remove: "წაშალეთ „{text}“",
    addLabel: "სახელის დამატება ({language})",
    placeholder: "სახელი ({language})",
    add: "დამატება",
    tooLong: "სახელი არაუმეტეს 200 სიმბოლოსი უნდა იყოს",
    duplicate: "ეს სახელი უკვე სიაშია",
    tooMany: "ერთ ენაზე არაუმეტეს სამი სახელი",
    suggest: "თარგმანების შეთავაზება",
    suggesting: "ვარჩევთ…",
    saveTitleFirst: "ჯერ შეინახეთ ახალი სათაური, შემდეგ მოითხოვეთ თარგმანები.",
    suggestedCount: {
      one: "შემოთავაზებულია {count} სახელი: გადაამოწმეთ ქვემოთ",
      other: "შემოთავაზებულია {count} სახელი: გადაამოწმეთ ქვემოთ",
    },
    nothingSuggested: "ახალი შესათავაზებელი არაფერია: ყველა ენაზე სახელი უკვე არის.",
  },
};
