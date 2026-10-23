/** `providerCircuits.*` texts in Russian (typed against providerCircuits.en.ts). */

import type { Translation } from "../../../translate";
import type { providerCircuitsEn } from "./providerCircuits.en";

export const providerCircuitsRu: Translation<typeof providerCircuitsEn> = {
  title: "Предохранители провайдеров",
  description:
    "У каждого провайдера, через которого отправляют обработчики, есть предохранитель. Пять сбоев за минуту размыкают его: сообщения ждут без обращения к провайдеру, а через 30 с проходит одна пробная отправка. Один провайдер занимает не больше половины потоков доставки обработчика.",
  none: "Ни один обработчик не сообщил о предохранителях",
  noneDescription: "Обработчики сообщают о предохранителях с каждым сигналом; обработчик прежнего выпуска о них не сообщает.",
  circuit: "Предохранитель",
  state: "Состояние",
  workers: "Обработчики, где не замкнут",
  workersOf: "{notClosed} из {total}",
  failures: "Сбои за минуту",
  opened: "Разомкнут",
  states: {
    closed: "Замкнут",
    half_open: "Пробная отправка",
    open: "Разомкнут",
  },
  providers: {
    meta: "Meta (WhatsApp, Messenger, Instagram)",
    telegram: "Боты Telegram",
    platform_bot: "Бот платформы",
    twilio_sms: "СМС (Twilio)",
    smtp: "Почта (SMTP)",
    flitt: "Платежи (Flitt)",
    web_push: "Веб-уведомления",
  },
};
