/** `loginOptions.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { loginOptionsEn } from "./loginOptions.en";

export const loginOptionsHe: Translation<typeof loginOptionsEn> = {
  channelLabel: "שליחת הקוד ב",
  noPhoneChannels: "כרגע אי אפשר לשלוח קודי כניסה למספרי טלפון מהמדינה הזו.",
  useEmail: "התחברות עם דוא״ל",
  nothingAvailable: "ההתחברות לא זמינה זמנית: עדיין אין דרך למסור קודי כניסה. נסו שוב מאוחר יותר.",
  restricted: "ההרשמה עדיין לא זמינה במדינה הזו.",
};
