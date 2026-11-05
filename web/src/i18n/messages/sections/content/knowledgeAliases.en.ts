/**
 * `knowledge.aliases.*` texts in English: the item's names in the business's
 * other languages, reviewed as chips in the knowledge editor. The reference
 * that the other languages are typed against.
 */

export const knowledgeAliasesEn = {
  aliases: {
    title: "Names in other languages",
    hint: "Customers ask in their own language. These names are searched like the title, and the ones you approve become starter questions of your website chat.",
    listLabel: "Names in {language}",
    none: "No name in {language} yet",
    suggested: "Suggested",
    suggestedHint: "Suggested names are already searched, but customers see them only after you accept them.",
    accept: "Accept “{text}”",
    remove: "Remove “{text}”",
    addLabel: "Add a name in {language}",
    placeholder: "Name in {language}",
    add: "Add",
    tooLong: "A name can have at most 200 characters",
    duplicate: "This name is already in the list",
    tooMany: "At most three names per language",
    suggest: "Suggest translations",
    suggesting: "Suggesting…",
    saveTitleFirst: "Save the new title first, then ask for translations.",
    suggestedCount: {
      one: "{count} name suggested: check it below",
      other: "{count} names suggested: check them below",
    },
    nothingSuggested: "Nothing new to suggest: every language already has a name.",
  },
} as const;
