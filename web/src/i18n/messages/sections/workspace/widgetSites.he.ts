/** `widgetSites.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { widgetSitesEn } from "./widgetSites.en";

export const widgetSitesHe: Translation<typeof widgetSitesEn> = {
  title: "אתרים שבהם הצ׳אט יכול להופיע",
  description:
    "הקוד של הצ׳אט עובד בכל אתר שמדביקים אותו בו. רשמו את האתרים שלכם והצ׳אט יעבוד רק בהם, כך שאף אחד לא יוכל להפעיל את העוזר שלכם, ואת המסלול שלכם, מעותק של הקוד.",
  anySite: "כל אתר",
  sites: { one: "אתר אחד", other: "{count} אתרים" },
  listLabel: "אתרים מורשים",
  empty: "עדיין אין רשימה: הצ׳אט עובד בכל אתר.",
  addLabel: "כתובת האתר",
  addHint: "כמו בשורת הכתובת של הדפדפן. כתובת עם www. ו-http או https נחשבות לאותו אתר.",
  placeholder: "https://cafe-batumi.ge",
  add: "הוספה",
  remove: "הסרת {site}",
  invalid: "זו לא כתובת אתר. הקלידו אותה כמו בשורת הכתובת של הדפדפן, למשל cafe-batumi.ge.",
  duplicate: "האתר הזה כבר ברשימה.",
  full: "הרשימה מכילה עד {count} אתרים.",
  alwaysAllowed: "עמוד הצ׳אט שלכם והתצוגה המקדימה בלוח הבקרה הזה תמיד עובדים.",
  ownerOnly: "רק בעלים יכולים לשנות את הרשימה הזו.",
  save: "שמירת הרשימה",
  saving: "שומרים…",
  unsaved: "לא נשמר",
  savedToast: "רשימת האתרים נשמרה",
  clearedToast: "הצ׳אט עובד שוב בכל אתר",
};
