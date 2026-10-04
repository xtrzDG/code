/** `digestChannels.*` texts: куда приходят сводки владельца (почта, устройства, Telegram, WhatsApp), на русском. */

import type { Translation } from "../../../translate";
import type { digestChannelsEn } from "./digestChannels.en";

export const digestChannelsRu: Translation<typeof digestChannelsEn> = {
  title: "Куда приходят",
  email: "Почта",
  emailTo: "На {email}",
  emailMissing: "Вы входите по телефону, поэтому почты для сводок нет.",
  emailNotReady: "Почта на этой платформе ещё не настроена.",
  push: "Устройства",
  devices: {
    one: "Уведомления включены на {count} устройстве",
    few: "Уведомления включены на {count} устройствах",
    many: "Уведомления включены на {count} устройствах",
    other: "Уведомления включены на {count} устройства",
  },
  noDevices: "Уведомления пока не включены ни на одном устройстве.",
  manageDevices: "Настройки уведомлений",
  telegram: "Telegram",
  telegramHint: "Полный отчёт от бота платформы.",
  telegramChat: "Чат Telegram",
  telegramNoChats: "Сначала подключите чат Telegram: «Каналы» → «Уведомления сотрудникам в Telegram».",
  openChannels: "Открыть «Каналы»",
  telegramNotReady: "Telegram на этой платформе ещё не настроен.",
  whatsapp: "WhatsApp",
  whatsappHint: "Короткая сводка со ссылкой с номера платформы.",
  whatsappNumber: "Ваш номер WhatsApp",
  whatsappNumberHint: "С кодом страны. Выбирая WhatsApp, вы соглашаетесь получать эти сообщения.",
  whatsappNotReady: "Сводки в WhatsApp на этой платформе ещё не настроены.",
  save: "Сохранить",
  saved: "Сохранено",
  invalidNumber: "Введите номер с кодом страны, например +995 555 12 34 56.",
  refusals: {
    telegramNotAvailable: "Сводки в Telegram на этой платформе ещё не настроены.",
    telegramChatNotLinked: "Этот чат больше не подключён к бизнесу. Выберите другой или подключите его снова.",
    whatsappNotAvailable: "Сводки в WhatsApp на этой платформе ещё не настроены.",
    whatsappNumberMissing: "Введите номер WhatsApp для сводок.",
  },
};
