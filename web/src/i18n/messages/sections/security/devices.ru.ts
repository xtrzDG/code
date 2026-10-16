import type { Translation } from "../../../translate";
import type { devicesEn } from "./devices.en";

/** `devices.*` по-русски: где выполнен вход в аккаунт. */
export const devicesRu: Translation<typeof devicesEn> = {
  title: "Где выполнен вход",
  description:
    "Все браузеры и телефоны, где вы вошли в аккаунт. Вход, которым не пользовались 7 дней, заканчивается сам.",
  descriptionAdmin:
    "Все браузеры и телефоны, где вы вошли в аккаунт. У админа платформы вход заканчивается через 12 часов без дела и через сутки после входа.",
  thisDevice: "Это устройство",
  kind: {
    desktop: "Компьютер",
    phone: "Телефон",
    tablet: "Планшет",
    unknown: "Устройство",
  },
  on: "{browser}, {system}",
  signedIn: "Вход {date}",
  lastUsed: "Последний раз {date}",
  from: "с адреса {address}",
  twoFactor: "С приложением-аутентификатором",
  oneFactor: "По коду входа",
  ends: "Закончится сам {date}",
  end: "Выйти",
  endLabel: "Выйти на устройстве {device}",
  endTitle: "Выйти на этом устройстве?",
  endDescription: "Тому, кто им пользуется, придётся войти снова.",
  ended: "Вход на устройстве завершён",
  endOthers: "Выйти на всех остальных",
  endOthersTitle: "Выйти на всех других устройствах?",
  endOthersDescription:
    "На всех браузерах и телефонах, кроме этого, придётся войти снова.",
  endedOthers: {
    one: "Выход на {count} устройстве",
    few: "Выход на {count} устройствах",
    many: "Выход на {count} устройствах",
    other: "Выход на {count} устройства",
  },
  onlyThis: "Вход выполнен только на этом устройстве.",
  notYou:
    "Не узнаёте устройство? Выйдите на нём и включите приложение-аутентификатор выше.",
};
