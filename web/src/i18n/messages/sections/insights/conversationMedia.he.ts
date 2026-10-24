/** `conversationMedia.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { conversationMediaEn } from "./conversationMedia.en";

export const conversationMediaHe: Translation<typeof conversationMediaEn> = {
  label: "קבצים מצורפים",
  kinds: {
    audio: "הודעה קולית",
    image: "תמונה",
    location: "מיקום",
    contact: "כרטיס איש קשר",
    sticker: "מדבקה",
    file: "קובץ",
  },
  voice: {
    transcript: "תמלול",
    play: "השמעה",
    playLabel: "השמעת ההודעה הקולית",
    playerLabel: "הודעה קולית מהלקוח",
    playerUnsupported: "הדפדפן שלכם לא יכול להשמיע כאן אודיו.",
    loading: "טוענים…",
    missing: "ההודעה הקולית הזו כבר לא זמינה: היא נמחקה אחרי תקופת השמירה או יחד עם הנתונים של הלקוח.",
    error: "לא הצלחנו לטעון את ההודעה הקולית. נסו שוב בעוד דקה.",
    retry: "לנסות שוב",
  },
  photo: {
    alt: "תמונה שהלקוח שלח",
    altWithCaption: "תמונה שהלקוח שלח: {caption}",
    open: "פתיחת התמונה",
    viewerTitle: "תמונה מהלקוח",
    unavailable: "לא ניתן להציג את התמונה: היא נמחקה, או שההתחברות שלכם הסתיימה.",
  },
  place: {
    openMap: "פתיחה במפות",
    openMapLabel: "פתיחת {place} במפות (נפתח בלשונית חדשה)",
    unnamed: "מיקום ששותף",
  },
  deleted: "הקובץ נמחק אחרי תקופת השמירה.",
  problems: {
    unsupported_kind: "העוזר לא יכול לקרוא את זה וביקש מהלקוח לכתוב במקום.",
    too_large: "גדול מדי לפתיחה: הלקוח התבקש לכתוב במקום.",
    too_long: "ארוך מדי לתמלול: הלקוח התבקש לכתוב במקום.",
    unavailable: "הקובץ כבר לא היה אצל המסנג׳ר: הלקוח התבקש לכתוב במקום.",
    unrecognized_format: "פורמט שהעוזר לא קורא: הלקוח התבקש לכתוב במקום.",
    not_understood: "לא ניתן היה לזהות מילים: הלקוח התבקש לכתוב במקום.",
  },
};
