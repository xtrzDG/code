/** `tunnelBusiness.*`: the business and where it is, in Russian. */

import type { Translation } from "../../../translate";
import type { tunnelBusinessEn } from "./tunnelBusiness.en";

export const tunnelBusinessRu: Translation<typeof tunnelBusinessEn> = {
  business: {
    title: "Как называется ваш бизнес?",
    text: "Мы создадим помощника, который будет отвечать вашим клиентам днём и ночью.",
    name: "Название бизнеса",
    namePlaceholder: "Например, «Кофейня на Руставели»",
    kindTitle: "Чем вы занимаетесь?",
    kindHint: "Выберите самое близкое. От этого зависит, о чём помощник спрашивает, что бронирует и что знает.",
    kindFixed: "Вы выбрали это при создании помощника, изменить уже нельзя.",
    legalReview: "Для такого бизнеса перед запуском помощника проводится короткая юридическая проверка.",
    detailsTitle: "О чём клиенты спрашивают всегда",
    errors: {
      name: "Напишите название бизнеса.",
      kind: "Выберите, чем занимается ваш бизнес.",
    },
  },
  place: {
    title: "Где вы находитесь?",
    text: "От страны зависят валюта, часовой пояс и языки ваших клиентов. Мы заполнили всё, что смогли.",
    country: "Страна",
    countryHint: "Цены в валюте {currency}",
    countryFixed: "Страну нельзя изменить после создания помощника.",
    city: "Город",
    cityPlaceholder: "Например, Тбилиси",
    address: "Адрес",
    addressPlaceholder: "Улица и дом",
    addressHint: "Помощник подскажет клиентам, как вас найти.",
    addressOptional: "необязательно",
    languages: "На каких языках пишут ваши клиенты",
    languagesHint: "Помощник отвечает каждому клиенту на его языке, если он есть в этом списке.",
    defaultLanguage: "Первое приветствие на языке",
    timezone: "Часовой пояс",
    creating: "Создаём вашего помощника…",
    errors: {
      country: "Выберите страну.",
      languages: "Выберите хотя бы один язык.",
      address: "Напишите адрес: по нему клиенты вас найдут.",
      restricted: "Бизнес из этой страны пока нельзя создать.",
    },
  },
};
