/** `supportAccess.*` in Hebrew: platform support in a cabinet (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { supportAccessEn } from "./supportAccess.en";

export const supportAccessHe: Translation<typeof supportAccessEn> = {
  label: "גישת התמיכה של הפלטפורמה",
  owner: {
    title: "התמיכה של הפלטפורמה צופה בלוח הבקרה שלכם",
    who: "{name}: „{reason}”",
    reason: "סיבה: „{reason}”",
    until: "עד {time}",
    readOnly: "התמיכה יכולה רק לצפות; שום דבר לא ישתנה בלעדיכם.",
    end: "סיום הגישה",
    endTitle: "לסיים את הגישה של התמיכה?",
    endDescription: "התמיכה תעזוב את לוח הבקרה שלכם מיד, וגם ההרשאה שלה לבצע שינויים תסתיים.",
    ended: "לתמיכה של הפלטפורמה כבר אין גישה",
    allow: "לאפשר לתמיכה לבצע שינויים",
    allowHint: "למשל, כשביקשתם שיגדירו בשבילכם את העוזר. מסתיים מעצמו.",
    allowedUntil: "התמיכה רשאית לבצע שינויים עד {time}",
    hours: "לכמה זמן",
    hourOptions: {
      one: "שעה אחת",
      two: "שעתיים",
      other: "{count} שעות",
    },
    dayOption: "יום",
    weekOption: "שבוע",
    allowed: "התמיכה רשאית לבצע שינויים",
    stopped: "התמיכה שוב יכולה רק לצפות",
    staff: "רק בעלים יכולים לסיים אותה או לאפשר לתמיכה לבצע שינויים.",
  },
  support: {
    title: "אתם צופים ב-{name} בתור התמיכה של הפלטפורמה",
    readOnly: "קריאה בלבד: שינויים נדחים.",
    canWrite: "הבעלים אישרו שינויים עד {time}",
    until: "הגישה מסתיימת ב-{time}",
    leave: "יציאה מלוח הבקרה",
    left: "יצאתם מלוח הבקרה",
  },
};
