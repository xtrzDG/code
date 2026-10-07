/** `assistantChat.*` in Hebrew: the test chat (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { assistantChatEn } from "./assistantChat.en";

export const assistantChatHe: Translation<typeof assistantChatEn> = {
  chat: {
    newConversation: "שיחה חדשה",
    logLabel: "שיחת ניסיון",
    emptyTitle: "התחילו שיחת ניסיון",
    emptyDescription: "שאלו מה שהלקוחות שלכם שואלים, בכל שפה. או נסו אחת מאלה:",
    suggestions: {
      hours: "מה שעות הפתיחה שלכם?",
      price: "כמה זה עולה?",
      booking: "אני רוצה להזמין למחר בשבע בערב ל-4 אנשים",
      human: "אפשר לדבר עם נציג?",
    },
    typing: "העוזר כותב…",
    choicesLabel: "תשובות לבחירה",
    inputLabel: "הודעה",
    placeholder: "כתבו הודעה…",
    inputHint: {
      one: "Enter שולח, Shift+Enter מוסיף שורה. עד תו אחד.",
      other: "Enter שולח, Shift+Enter מוסיף שורה. עד {count} תווים.",
    },
    send: "שליחה",
    failed: "לא נשלח.",
    silent: "העוזר שותק: השיחה הועברה לאדם.",
    handedOffTitle: "הועבר לאדם",
    handedOffDescription: "בצ׳אט אמיתי הצוות שלכם היה עונה עכשיו, ולכן העוזר שותק. התחילו שיחה חדשה כדי להמשיך לנסות.",
    guardRewritten: "המספרים נבדקו ותוקנו",
    guardHandedOff: "הועבר הלאה: אין ודאות לגבי מספר",
    handedOff: "הועבר לאדם",
    bookingsCreated: { one: "נוצרה הזמנת ניסיון", other: "נוצרו {count} הזמנות ניסיון" },
    leadsCreated: { one: "נוצרה פניית ניסיון", other: "נוצרו {count} פניות ניסיון" },
    toolCalls: { one: "קריאה אחת לכלי", other: "{count} קריאות לכלים" },
    toolError: "שגיאה",
    toolInput: "קלט",
    toolResult: "תוצאה",
    noVersionsTitle: "עדיין אין מה לנסות",
    noVersionsDescription: "החילו את השינויים שלכם כדי להכין את העדכון הראשון של העוזר, ואז דברו איתו כאן.",
    errors: {
      service: "מודל השפה לא זמין כרגע. נסו שוב בעוד דקה.",
    },
  },
};
