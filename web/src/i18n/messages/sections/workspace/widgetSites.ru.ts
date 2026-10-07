/** `widgetSites.*` texts in Russian (typed against widgetSites.en.ts). */

import type { Translation } from "../../../translate";
import type { widgetSitesEn } from "./widgetSites.en";

export const widgetSitesRu: Translation<typeof widgetSitesEn> = {
  title: "Сайты, на которых работает чат",
  description:
    "Код чата работает на любом сайте, куда его вставили. Перечислите свои сайты, и чат будет работать только на них: никто не запустит вашего помощника и ваш тариф с копии кода.",
  anySite: "Любой сайт",
  sites: { one: "{count} сайт", few: "{count} сайта", many: "{count} сайтов", other: "{count} сайта" },
  listLabel: "Разрешённые сайты",
  empty: "Списка пока нет: чат работает на любом сайте.",
  addLabel: "Адрес сайта",
  addHint: "Как в адресной строке браузера. Адрес с www. и без, http и https считаются одним сайтом.",
  placeholder: "https://cafe-batumi.ge",
  add: "Добавить",
  remove: "Убрать {site}",
  invalid: "Это не адрес сайта. Введите его как в адресной строке браузера, например cafe-batumi.ge.",
  duplicate: "Этот сайт уже в списке.",
  full: {
    one: "В списке может быть до {count} сайта.",
    few: "В списке может быть до {count} сайтов.",
    many: "В списке может быть до {count} сайтов.",
    other: "В списке может быть до {count} сайта.",
  },
  alwaysAllowed: "Страница вашего чата и предпросмотр в кабинете работают всегда.",
  ownerOnly: "Менять список может только владелец.",
  save: "Сохранить список",
  saving: "Сохраняем…",
  unsaved: "Не сохранено",
  savedToast: "Список сайтов сохранён",
  clearedToast: "Чат снова работает на любом сайте",
};
