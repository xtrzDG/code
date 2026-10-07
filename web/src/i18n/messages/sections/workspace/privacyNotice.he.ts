/** `privacyNotice.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { privacyNoticeEn } from "./privacyNotice.en";

export const privacyNoticeHe: Translation<typeof privacyNoticeEn> = {
  title: "הודעת פרטיות",
  subtitle: "איך {business} מטפל במה שאתם כותבים בצ׳אט שלו",
  whoTitle: "מי עונה",
  who: "{business} עונה להודעות בעזרת עוזר בינה מלאכותית – באתר שלו, בדף הזה ובאפליקציות מסרים. Assistant Workshop מספקת את העוזר ומעבדת את ההודעות שלכם בשם {business}, שמחליט מה ייעשה בהן.",
  whatTitle: "מה נשמר",
  whatMessages: "מה שאתם כותבים בצ׳אט ותשובות העוזר.",
  whatContacts: "השם, מספר הטלפון או הדוא״ל שלכם, אם תמסרו אותם (למשל להזמנה או לחזרה טלפונית).",
  whatBrowser: "מפתח אקראי באחסון של הדפדפן, כדי שהצ׳אט ימשיך מהמקום שבו עצרתם. הצ׳אט לא משתמש בעוגיות.",
  whatTechnical: "נתונים טכניים כמו כתובת ה-IP שלכם, שנשמרים לזמן קצר כדי להגן על הצ׳אט מפני ניצול לרעה.",
  whyTitle: "למה",
  why: "כדי לענות על שאלותיכם, לקבל הזמנות ובקשות ולהעביר את השיחה לצוות של {business} כשאתם מבקשים אדם או כשהעוזר לא יכול לעזור.",
  sharedTitle: "מי רואה את זה",
  shared: "הצוות של {business}. כדי לכתוב תשובות, טקסט השיחה מעובד על ידי ספק מודל הבינה המלאכותית שעליו פועל העוזר, למטרה זו בלבד.",
  keptTitle: "לכמה זמן",
  kept: "{business} שומר את השיחות {conversations} אחרי ההודעה האחרונה שלהן, ואז הן נמחקות אוטומטית, ואת הרישומים של קריאות ה-AI של העוזר {modelRecords}. אפשר לבקש בכל עת למחוק את שלכם.",
  rightsTitle: "הבחירות שלכם",
  rights: "אפשר לשאול את {business} מה נשמר עליכם ולבקש לתקן או למחוק: כתבו בצ׳אט או פנו לעסק ישירות. העוזר עלול לטעות, לכן בדקו פרטים חשובים (מחירים, שעות) מול העסק.",
  platformNote: "זוהי הודעת ברירת המחדל של פלטפורמת Assistant Workshop. {business} רשאי לפרסם הודעה משלו.",
  backToChat: "חזרה לצ׳אט",
};
