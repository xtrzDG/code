/** `bookingCalendar.*` in Hebrew: the bookings calendar (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { bookingCalendarEn } from "./bookingCalendar.en";

export const bookingCalendarHe: Translation<typeof bookingCalendarEn> = {
  views: {
    label: "הצגת ההזמנות",
    list: "רשימה",
    day: "יום",
    week: "שבוע",
    nights: "לילות",
  },
  toolbar: {
    label: "תאריכי היומן",
    previous: { day: "היום הקודם", week: "השבוע הקודם", nights: "לילות מוקדמים יותר" },
    next: { day: "היום הבא", week: "השבוע הבא", nights: "לילות מאוחרים יותר" },
    today: "היום",
    date: "תאריך",
    includeTest: "הצגת הזמנות בדיקה",
  },
  loading: "היומן נטען…",
  truncated: "בתקופה זו יש יותר הזמנות ממה שהיומן יכול להציג בבת אחת. פתחו תקופה קצרה יותר או את הרשימה.",
  legend: "סטטוס ההזמנה",
  moveHint: "גררו הזמנה לשעה או למקום אחרים. או בחרו אותה והזיזו בעזרת החצים: Enter מעביר, Escape מבטל.",
  day: {
    label: "הזמנות ליום {date} לפי מקום",
    closed: "סגור",
    closedDay: "סגור כל היום",
    newAt: "הזמנה חדשה: {place}",
    booked: "{percent} תפוס",
    now: "עכשיו {time}",
    noPlacesTitle: "אין מקומות שמוזמנים לפי שעה",
    noPlacesDescription: "הוסיפו שולחנות, אנשי צוות או אולמות שמוזמנים לפי שעה, והיום יציג כל אחד מהם כעמודה.",
    toPlaces: "הוספת מקומות",
  },
  block: {
    label: "{name}, {time}, {place}, {status}",
    test: "בדיקה",
  },
  move: {
    pending: "להעביר אל {place}, {time}? Enter מעביר, Escape מבטל.",
    pendingStay: "להעביר אל {place} מ־{date}? Enter מעביר, Escape מבטל.",
    moved: "הועבר אל {place}, {time}",
    movedStay: "הועבר אל {place} מ־{date}",
    undone: "ההזמנה חזרה למקומה",
    changed: "מישהו שינה את ההזמנה הזו לפני רגע: היומן מציג אותה כפי שהיא עכשיו.",
    cancelled: "ההעברה בוטלה",
    tell: {
      title: "יש לעדכן את {name} בשעה החדשה",
      titleAnonymous: "יש לעדכן את הלקוח בשעה החדשה",
      hint: "העוזר לא שולח ללקוחות הודעה על העברות שנעשו בלוח השנה. אפשר להעתיק את הטקסט ולשלוח אותו בערוץ שבו אתם מדברים.",
      show: "הצגת ההודעה",
    },
  },
  week: {
    label: "עד כמה כל מקום מלא, {range}",
    place: "מקום",
    allPlaces: "כל המקומות",
    closed: "סגור",
    free: "פנוי",
    share: "{percent} תפוס",
    rooms: { one: "{booked} מתוך חדר אחד תפוס", other: "{booked} מתוך {open} חדרים תפוסים" },
    cell: "{place}, {date}: {load}, {count}",
    legendTitle: "תפוסה",
    quiet: "שקט",
    full: "מלא",
  },
  nights: {
    label: "חדרים לפי לילה, {range}",
    room: "חדר",
    taken: "{booked} מתוך {open} תפוסים",
    newStay: "שהייה חדשה: {place}, הלילה של {date}",
    noRoomsTitle: "אין חדרים שמוזמנים לפי לילה",
    noRoomsDescription: "הוסיפו חדרים או סוגי חדרים שמוזמנים לפי לילה, וכל אחד יופיע כאן כשורה.",
  },
};
