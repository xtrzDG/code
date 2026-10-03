/** `loginOptions.*` texts of the sign-in code channels, in Russian. */

import type { Translation } from "../../../translate";
import type { loginOptionsEn } from "./loginOptions.en";

export const loginOptionsRu: Translation<typeof loginOptionsEn> = {
  channelLabel: "Прислать код через",
  noPhoneChannels: "Сейчас коды входа нельзя отправить на номера этой страны.",
  useEmail: "Войти по почте",
  nothingAvailable: "Вход временно недоступен: пока нет способа доставить код. Попробуйте позже.",
  restricted: "Регистрация в этой стране пока недоступна.",
};
