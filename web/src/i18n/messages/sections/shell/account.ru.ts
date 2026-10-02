/** `account.*` texts: the user menu and installing the cabinet as an app, in Russian. */

import type { Translation } from "../../../translate";
import type { accountEn } from "./account.en";

export const accountRu: Translation<typeof accountEn> = {
  menu: "Аккаунт и предпочтения",
  signedInAs: "Вы вошли как",
  preferences: "Предпочтения",
  businesses: "Все бизнесы",
  admin: "Администратор платформы",
  install: "Установить приложение",
  installHint: "Открывайте кабинет с главного экрана или из дока, как приложение.",
  installIosTitle: "Установка на iPhone или iPad",
  installIosSteps: "В Safari нажмите «Поделиться» внизу экрана, затем «На экран „Домой“».",
  installed: "Приложение установлено",
};
