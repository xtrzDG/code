/** `account.*` in Hebrew: the user menu (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { accountEn } from "./account.en";

export const accountHe: Translation<typeof accountEn> = {
  menu: "חשבון והעדפות",
  signedInAs: "מחובר בתור",
  preferences: "העדפות",
  businesses: "כל העסקים",
  admin: "ניהול הפלטפורמה",
  install: "התקנת האפליקציה",
  installHint: "פתחו את לוח הבקרה ממסך הבית או מסרגל היישומים, כמו אפליקציה.",
  installIosTitle: "התקנת האפליקציה ב-iPhone או ב-iPad",
  installIosSteps: "ב-Safari, הקישו על „שיתוף” בתחתית המסך ואז על „הוספה למסך הבית”.",
};
