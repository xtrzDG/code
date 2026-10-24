/** `quality.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { qualityEn } from "./quality.en";

export const qualityHe: Translation<typeof qualityEn> = {
  admin: {
    title: "איכות השיחות, 30 ימים",
    description: "בכל לילה שופט AI נותן ציון למדגם קטן של שיחות אמיתיות לפי חמשת קריטריוני הבדיקה. ציונים בלבד, בלי טקסט של לקוחות.",
    empty: "לא נשפטו שיחות ב-30 הימים האחרונים.",
    average: "ממוצע, 30 ימים",
    lastWeek: "7 הימים האחרונים",
    previousWeek: "7 הימים שלפני: {score}",
    judged: "שיחות שנשפטו",
    dropping: "ירידה של {percent}%",
    droppingNote: "השבוע האחרון קיבל ציון נמוך ב-{percent}% מהשבוע שלפניו. פתחו את השיחות עם הציון הנמוך ביותר למטה ואת העדכון האחרון של הלקוח.",
    scoreValue: "{score} / 5",
    trendLabel: "ציון ממוצע ליום, 30 הימים האחרונים",
    noScoresDay: "{date}: לא נשפט",
    dayValue: "{date}: {score} / 5 על פני {count}",
    showTable: "הצגה כטבלה",
    day: "יום",
    count: "נשפטו",
    lowestTitle: "השיחות עם הציון הנמוך ביותר",
    lowestCaption: "חמשת הציונים הנמוכים ביותר ב-30 הימים",
    judgedAt: "נשפטה",
    channel: "ערוץ",
    language: "שפה",
    score: "ציון",
    weak: "נקודות חלשות",
    noWeak: "אין מתחת ל-4",
  },
  conversation: {
    title: "הציון של שופט ה-AI",
    description: "השיחה הזו הייתה במדגם האיכות הלילי.",
    judgedAt: "נשפטה {date}",
    notes: "הערות",
  },
};
