/** `knowledge.aliases.*` in Hebrew: the item's names in the business's other languages (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { knowledgeAliasesEn } from "./knowledgeAliases.en";

export const knowledgeAliasesHe: Translation<typeof knowledgeAliasesEn> = {
  aliases: {
    title: "שמות בשפות אחרות",
    hint: "לקוחות שואלים בשפה שלהם. השמות האלה נמצאים בחיפוש כמו הכותרת, ואלה שתאשרו הופכים לשאלות פתיחה בצ׳אט של האתר.",
    listLabel: "שמות ב{language}",
    none: "עדיין אין שם ב{language}",
    suggested: "הצעה",
    suggestedHint: "שמות מוצעים כבר נמצאים בחיפוש, אבל לקוחות יראו אותם רק אחרי שתאשרו.",
    accept: "אישור „{text}”",
    remove: "הסרת „{text}”",
    addLabel: "הוספה: שם ב{language}",
    placeholder: "שם ב{language}",
    add: "הוספה",
    tooLong: "שם יכול להכיל עד 200 תווים",
    duplicate: "השם הזה כבר ברשימה",
    tooMany: "עד שלושה שמות לכל שפה",
    suggest: "הצעת תרגומים",
    suggesting: "מחפשים הצעות…",
    saveTitleFirst: "שמרו קודם את הכותרת החדשה, ואז בקשו תרגומים.",
    suggestedCount: {
      one: "הוצע שם אחד: בדקו אותו למטה",
      other: "הוצעו {count} שמות: בדקו אותם למטה",
    },
    nothingSuggested: "אין מה להציע: לכל שפה כבר יש שם.",
  },
};
