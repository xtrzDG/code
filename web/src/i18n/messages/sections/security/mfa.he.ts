/** `mfa.*` in Hebrew: two-factor sign-in (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { mfaEn } from "./mfa.en";

export const mfaHe: Translation<typeof mfaEn> = {
  secondStep: {
    title: "התחברות דו-שלבית",
    description: "פתחו את אפליקציית האימות והזינו את הקוד בן 6 הספרות שהיא מציגה עבור Assistant Workshop.",
    code: "קוד מהאפליקציה",
    recoveryDescription: "הזינו אחד מקודי השחזור ששמרתם. כל קוד עובד פעם אחת.",
    recoveryCode: "קוד שחזור",
    recoveryHint: "12 אותיות וספרות, למשל {example}",
    useRecovery: "שימוש בקוד שחזור במקום",
    useApp: "שימוש באפליקציית האימות",
    verify: "התחברות",
    verifying: "בודקים…",
    startOver: "התחברות מחדש",
  },
  enrollment: {
    title: "הגדרת התחברות דו-שלבית",
    description:
      "מנהלי הפלטפורמה מתחברים גם עם קוד מאפליקציית אימות. הגדירו אחת עכשיו: זה לוקח דקה, וההתחברויות הבאות יבקשו רק את הקוד.",
    start: "הגדרה עכשיו",
    starting: "מכינים…",
  },
  setup: {
    title: "הגדרת אפליקציית אימות",
    stepInstall: "התקינו אפליקציית אימות בטלפון: Google Authenticator, Microsoft Authenticator, 1Password או אחרת.",
    stepScan: "סרקו את קוד ה-QR הזה באפליקציה, או הקלידו את המפתח.",
    stepCode: "הזינו את הקוד בן 6 הספרות שהאפליקציה מציגה.",
    qrLabel: "קוד QR לאפליקציית האימות",
    key: "מפתח",
    copyKey: "העתקת המפתח",
    code: "קוד מהאפליקציה",
    confirm: "הפעלה",
    confirming: "מפעילים…",
  },
  recovery: {
    title: "שמרו את קודי השחזור",
    description:
      "אם הטלפון יאבד, התחברו עם אחד מהקודים האלה במקום האפליקציה. כל קוד עובד פעם אחת. הם מוצגים רק עכשיו: שמרו אותם במנהל סיסמאות או הדפיסו אותם.",
    copy: "העתקה",
    download: "הורדה",
    fileHeading: "קודי השחזור של Assistant Workshop עבור {account}. כל קוד עובד פעם אחת.",
    saved: "שמרתי את הקודים במקום בטוח",
    continue: "המשך",
  },
  stepUp: {
    title: "אשרו שזה אתם",
    description: "הפעולה הזו דורשת אישור עדכני.",
    totp: "הזינו את הקוד מאפליקציית האימות.",
    loginCode: "שלחנו קוד אל {destination}. הזינו אותו כאן.",
    sending: "שולחים קוד…",
    code: "קוד",
    confirm: "אישור",
    confirming: "בודקים…",
    resend: "שליחת קוד חדש",
    confirmed: "אושר. מבצעים עכשיו.",
  },
  errors: {
    wrongCode: "הקוד שגוי או שכבר נעשה בו שימוש. נסו את הקוד החדש ביותר.",
    expired: "פג תוקף ההתחברות הזו. התחילו מחדש.",
    tooManyAttempts: "יותר מדי קודים שגויים. התחברו מחדש.",
    codeFormat: "הזינו 6 ספרות",
  },
};
