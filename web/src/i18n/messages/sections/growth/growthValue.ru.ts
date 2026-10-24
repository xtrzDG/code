/** `growthValue.*` по-русски: брони из листа ожидания и после сообщений о повторном визите. */

import type { Translation } from "../../../translate";
import type { growthValueEn } from "./growthValue.en";

export const growthValueRu: Translation<typeof growthValueEn> = {
  label: "Брони, которые помощник вернул",
  waitlist: {
    one: "{count} из листа ожидания",
    few: "{count} из листа ожидания",
    many: "{count} из листа ожидания",
    other: "{count} из листа ожидания",
  },
  campaign: {
    one: "{count} после сообщения о повторном визите",
    few: "{count} после сообщений о повторном визите",
    many: "{count} после сообщений о повторном визите",
    other: "{count} после сообщений о повторном визите",
  },
  worth: "≈ {money}",
  waitlistHint: "Освободившиеся места, которые заняли ждавшие клиенты.",
  campaignHint: "Клиенты, которые записались снова после сообщения.",
  rows: {
    waitlistBookings: "Брони из листа ожидания",
    waitlistValue: "Сумма броней из листа ожидания",
    campaignBookings: "Брони после сообщений о повторном визите",
    campaignValue: "Сумма броней после сообщений о повторном визите",
  },
};
