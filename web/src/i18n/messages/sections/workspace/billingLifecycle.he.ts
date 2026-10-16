/** `billingLifecycle.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { billingLifecycleEn } from "./billingLifecycle.en";

export const billingLifecycleHe: Translation<typeof billingLifecycleEn> = {
  reasons: {
    too_expensive: "זה עולה יותר מדי",
    seasonal_break: "אנחנו סגורים לעונה",
    not_enough_use: "מעט מדי לקוחות כותבים או מתקשרים כרגע",
    missing_feature: "הוא לא יודע לעשות משהו שאנחנו צריכים",
    answer_quality: "התשובות לא מספיק טובות",
    switched_provider: "אנחנו עוברים לשירות אחר",
    closing_business: "אנחנו סוגרים את העסק",
    somethingElse: "משהו אחר",
  },
  cancel: {
    reasonLegend: "מה הסיבה העיקרית?",
    reasonHint: "זה עוזר לנו להשתפר, ואולי יש משהו שמתאים לכם יותר מביטול.",
    detailsLabel: "רוצים להוסיף משהו?",
    detailsPlaceholder: "במילים שלכם",
    continue: "המשך",
    offerTitle: "לפני שאתם הולכים",
    cancelAnyway: "לא, לבטל בכל זאת",
    back: "חזרה",
  },
  offerKinds: {
    pause: "הפסקה עונתית",
    downgrade: "מסלול זול יותר",
    credit: "זיכוי חד-פעמי",
  },
  offers: {
    pause: {
      title: "קחו הפסקה עונתית במקום",
      description:
        "חודש מושהה עולה {price}: העוזר ממשיך לרשום פניות, הערוצים נשארים מחוברים, והשירות המלא חוזר מעצמו.",
      confirm: { one: "השהיה לחודש אחד", two: "השהיה לחודשיים", other: "השהיה ל-{count} חודשים" },
    },
    downgrade: {
      title: "שמרו את העוזר בפחות",
      description: "„{plan}” עולה {price}. התשובות, הערוצים וההגדרות נשארים כמו שהם; המחיר החדש חל מהחשבון הבא.",
      confirm: "מעבר ל„{plan}”",
    },
    credit: {
      title: "הישארו, ו-{amount} עלינו",
      description: "נוסיף {amount} לחשבון שלכם; הסכום יורד מהחשבון הבא.",
      confirm: "לקבל את הזיכוי",
    },
    taken: {
      pause: "ההפסקה נקבעה",
      downgrade: "המסלול שונה",
      credit: "הזיכוי נמצא בחשבון שלכם",
    },
  },
  pause: {
    title: "הפסקה עונתית",
    description:
      "סגורים לעונה? השהו במקום לבטל: העוזר ממשיך לרשום פניות, הערוצים נשארים מחוברים, והשירות המלא חוזר מעצמו.",
    price: "{price} לחודש, {percent}% מהמסלול שלכם",
    monthsLegend: "לכמה זמן",
    months: { one: "חודש אחד", two: "חודשיים", other: "{count} חודשים" },
    window: "מ-{start} עד {until}",
    submit: "השהיה מ-{date}",
    allowance: "הושהה {months} {window}.",
    allowanceMonths: { one: "{used} מתוך חודש אחד", other: "{used} מתוך {cap} חודשים" },
    allowanceWindow: { one: "בחודש האחרון", other: "ב-{window} החודשים האחרונים" },
    scheduledTitle: "ההפסקה נקבעה",
    scheduled:
      "מ-{start} עד {until} העוזר רק רושם פניות. התשלומים האוטומטיים כבויים; תשלומים במחיר מלא יתחדשו אחרי ההפסקה.",
    callOff: "ביטול ההפסקה",
    calledOff: "ההפסקה בוטלה",
    pausedTitle: "בהפסקה עד {date}",
    paused: "העוזר רק רושם פניות; הערוצים נשארים מחוברים. כל חודש מושהה מחויב ב-{percent}% מהמסלול שלכם.",
    resume: "חידוש השירות המלא",
    resumeTitle: "לחדש את השירות המלא עכשיו?",
    resumeDescription:
      "העוזר שוב עונה ללקוחות ומקבל הזמנות. אם חודש ההפסקה הזה כבר שולם, השירות המלא חוזר כשהוא מסתיים; אחרת עכשיו, והתקופה הבאה לתשלום.",
    resumed: "השירות המלא חוזר",
    plansHint: "בזמן ההפסקה המסלול נשאר כמו שהוא; חדשו את השירות המלא כדי לשנות אותו.",
    unavailable: {
      not_active: "הפסקה אפשרית במינוי חודשי ששולם.",
      not_monthly: "אי אפשר להשהות מסלול שנתי.",
      allowance_used: "ארבעה חודשי הפסקה נוצלו בשנים-עשר החודשים האחרונים; אפשר להשהות שוב מאוחר יותר.",
    },
  },
  facts: {
    pause: "הפסקה עונתית",
  },
  errors: {
    offerGone: "ההצעה הזו כבר לא זמינה. סגרו את החלון ונסו שוב.",
    pauseGone: "הפסקה לא אפשרית כרגע. טענו את העמוד מחדש כדי לראות למה.",
  },
};
