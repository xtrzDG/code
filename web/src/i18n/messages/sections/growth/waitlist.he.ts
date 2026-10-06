/** `waitlist.*` in Hebrew: Bookings → Waitlist (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { waitlistEn } from "./waitlist.en";

export const waitlistHe: Translation<typeof waitlistEn> = {
  loading: "טוענים את רשימת ההמתנה…",
  filters: {
    label: "אילו רשומות",
    active: "ממתינים",
    booked: "הזמינו",
    ended: "הסתיימו",
  },
  empty: {
    active: "אף אחד לא ממתין",
    activeDescription:
      "כשיום מלא, העוזר מציע ללקוח להיכנס לרשימת ההמתנה. מקום שמתפנה בעקבות ביטול או העברה מוצע לראשון שהוא מתאים לו.",
    booked: "עדיין אין הזמנות מרשימת ההמתנה",
    bookedDescription: "לקוחות שאמרו כן למקום שהתפנה מופיעים כאן עם ההזמנה שלהם.",
    ended: "עדיין שום דבר לא הסתיים",
    endedDescription: "רשומות מסתיימות כשהלקוח אומר לא, לא עונה בזמן, או כשהיום עובר.",
  },
  customer: "לקוח",
  wants: "רוצה את {date}",
  window: {
    any: "בכל שעה",
    between: "{from}–{to}",
    from: "מ-{from}",
    until: "עד {to}",
  },
  nights: { one: "לילה אחד", two: "שני לילות", other: "{count} לילות" },
  status: {
    waiting: "ממתין",
    offered: "מקום שמור",
    booked: "הזמין",
    expired: "הסתיים",
  },
  endReasons: {
    declined: "אמר לא למקום",
    no_answer: "לא ענה בזמן",
    date_passed: "היום עבר",
    unreachable: "לא היה אפשר להשיג אותו",
    removed: "הוסר מהרשימה",
  },
  offer: {
    held: "שמור עבורו: {place}, {time}",
    heldNoPlace: "שמור עבורו: {time}",
    until: "עד {time}",
    minutesLeft: { one: "נותרה דקה אחת", two: "נותרו שתי דקות", other: "נותרו {count} דקות" },
    answerDue: "ממתינים לתשובה",
  },
  offerCount: { one: "הוצע לו מקום פעם אחת", two: "הוצע לו מקום פעמיים", other: "הוצע לו מקום {count} פעמים" },
  joined: "הצטרף {time}",
  booked: "הזמין {time}",
  ended: "הסתיים {time}",
  openConversation: "פתיחת השיחה",
  remove: "הסרה מהרשימה",
  removeTitle: "להסיר את {name} מרשימת ההמתנה?",
  removeBody: "לא יוצע לו מקום שמתפנה. מקום שנשמר עבורו כרגע יעבור לבא בתור.",
  removeConfirm: "הסרה מהרשימה",
  removed: "הוסר מרשימת ההמתנה",
  showMore: "להציג עוד",
  timeZone: "השעות לפי {timezone}.",
  settings: {
    title: "הגדרות רשימת ההמתנה",
    description:
      "הזמנה שבוטלה או הועברה מפנה מקום: הוא נשמר ללקוח הראשון שהוא מתאים לו ומוצע לו בערוץ ובשפה שלו. „כן” מזמין אותו.",
    toggle: "ניהול רשימת המתנה",
    off: "העוזר לא מציע את רשימת ההמתנה. לקוחות שכבר נמצאים בה נשארים עד היום שלהם.",
    hold: "לשמור מקום שהתפנה למשך",
    holdHint: "אם לא תגיע תשובה עד אז, המקום עובר לבא בתור.",
    holdOption: { one: "דקה אחת", two: "שתי דקות", other: "{count} דקות" },
    save: "שמירה",
    saved: "הגדרות רשימת ההמתנה נשמרו",
    ownersOnly: "רק בעלים יכולים לשנות את ההגדרות האלה.",
  },
};
