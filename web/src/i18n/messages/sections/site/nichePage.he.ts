/** `nichePage.*` in Hebrew: a public page for one kind of business (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { nichePageEn } from "./nichePage.en";

export const nichePageHe: Translation<typeof nichePageEn> = {
  metaTitle: "{niche}: עוזר AI לשיחות ולהודעות",
  metaDescription:
    "{description} העוזר עונה יומם ולילה בשפות של הלקוחות שלכם, מקבל הזמנות ופניות ומעביר מקרים מורכבים לצוות שלכם.",
  breadcrumb: "סוגי עסקים",
  eyebrow: "עוזר AI לסוג העסק הזה",
  title: "{niche}: מענה לכל שיחה והודעה",
  lead: "העוזר יודע מה לקוחות של סוג העסק הזה שואלים בדרך כלל, עונה לפי המחירים והכללים שלכם ולעולם לא ממציא.",
  primary: "יצירת עוזר",
  secondary: "לנסות את ההדגמה",
  doesTitle: "מה העוזר עושה כאן",
  books: "מזמין: {resource}, לפי שעות הפתיחה והמקומות הפנויים שלכם",
  noBookings: "רושם הזמנות ופניות עם הפרטים שהצוות שלכם צריך",
  answers: "עונה על שאלות לגבי מחירים, שעות וכללים בשפת הלקוח",
  handoff: "מעביר תלונות ובקשות חריגות לאדם עם סיכום קצר",
  sensitive: "שאלות רגישות (בריאות, בטיחות, משפט) תמיד עוברות לאדם: העוזר לא מייעץ בהן",
  integrationsTitle: "עובד עם",
  plansTitle: "מסלולים מתאימים",
  plansText: "עסקים כאלה בדרך כלל מתחילים עם {plans}. לכל מסלול יש תקופת ניסיון חינם.",
  pricingLink: "לצפייה במחירים",
  demoTitle: "שוחחו עם עוזר הדגמה",
  demoText: "עסק הדגמה מהסוג הזה עונה כמו אמיתי; שום דבר לא מוזמן באמת.",
  otherTitle: "סוגי עסקים אחרים",
  notFound: "אין סוג עסק כזה.",
};
