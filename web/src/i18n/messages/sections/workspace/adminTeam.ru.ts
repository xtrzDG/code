/** `adminTeam.*` texts of the platform admin team page, in Russian. */

import type { Translation } from "../../../translate";
import type { adminTeamEn } from "./adminTeam.en";

export const adminTeamRu: Translation<typeof adminTeamEn> = {
  nav: "Команда",
  title: "Команда админов",
  description:
    "Кто может открывать админку и что может каждая роль. Каждое изменение записывается в журнал аудита.",
  roles: {
    super: "Главный админ",
    support_readonly: "Поддержка (только просмотр)",
    billing: "Оплаты",
  },
  roleHints: {
    super: "Всё: клиенты, работа платформы, метрики, команда; изменения в кабинете клиента, если владелец разрешил.",
    support_readonly: "Клиенты и состояние платформы; открывает кабинет клиента на час, только для просмотра.",
    billing: "Клиенты и метрики роста; кабинеты клиентов не открывает.",
  },
  you: "Вы",
  notSignedIn: "Ещё не входил",
  addedBy: "Добавил(а) {name} {date}",
  addedOn: "Добавлен(а) на странице «Команда» {date}",
  bootstrapped: "Из списков PLATFORM_ADMIN_* {date}",
  role: "Роль",
  roleFor: "Роль: {name}",
  changed: "Роль изменена",
  remove: "Убрать",
  removeLabel: "Убрать {name} из команды",
  removeTitle: "Убрать {name} из команды админов?",
  removeDescription: "Админка закроется для этого человека при следующем запросе.",
  removed: "Убран(а) из команды",
  add: "Добавить человека",
  addTitle: "Добавить человека в команду админов",
  addDescription:
    "Админка откроется при следующем входе с этим номером или почтой; понадобится приложение-аутентификатор.",
  by: "Входит по",
  byPhone: "Номеру телефона",
  byEmail: "Почте",
  phone: "Номер телефона",
  email: "Почта",
  added: "Добавлен(а) в команду",
  lastSuper: "В команде должен остаться хотя бы один главный админ: сначала дайте эту роль кому-то ещё.",
};
