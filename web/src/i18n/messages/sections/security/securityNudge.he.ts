/** `securityNudge.*` texts in Hebrew: the owner's second-factor banner. */

import type { Translation } from "../../../translate";
import type { securityNudgeEn } from "./securityNudge.en";

export const securityNudgeHe: Translation<typeof securityNudgeEn> = {
  title: "הגנו על נתוני הלקוחות: הפעילו גורם שני",
  description:
    "עם מפתח גישה או אפליקציית אימות, קוד כניסה גנוב לבדו לא יפתח את לוח הבקרה שלכם.",
  teamGrew:
    "הצוות שלכם גדל: יותר אנשים יכולים לראות את נתוני הלקוחות. הפעילו גורם שני.",
  action: "הפעלה",
  dismiss: "לא עכשיו",
  dismissLabel: "הסתרת התזכורת על גורם שני",
};
