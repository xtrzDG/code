/** `knowledge.offer.*` texts of bookable offers, in Russian. */

import type { Translation } from "../../../translate";
import type { knowledgeOfferEn } from "./knowledgeOffer.en";

export const knowledgeOfferRu: Translation<typeof knowledgeOfferEn> = {
  offer: {
    nightlyPrice: "Цена за ночь, {currency}",
    nightlyPriceHint: "Столько стоят ночи вне всех сезонов. Оставьте пустым, если цена от чего-то зависит.",
    durationHint: "От 5 до 720 минут: столько длится запись.",
    buffer: "Перерыв после, мин",
    bufferHint: "Столько исполнитель занят после услуги (уборка, подготовка).",
    performers: "Кто выполняет",
    performersHint: "Записывать будут только к ним. Никто не отмечен — к любому, кто не привязан к конкретным услугам.",
    rooms: "Номера этого типа",
    roomsHint: "Проживание этого типа бронируется в одном из этих номеров. Ни один не отмечен — в любом номере с посуточной бронью.",
    noResources: "Выбирать пока не из кого: сначала добавьте сотрудников или места с почасовой записью.",
    noRooms: "Номеров с посуточной бронью пока нет: сначала добавьте их.",
    toResources: "Открыть «Ресурсы и часы»",
    resourceOff: "выключен",
    filter: "Найти по имени",
    noMatches: "Никого по запросу «{query}»",
    selectedCount: { one: "Выбран {count}", few: "Выбрано {count}", many: "Выбрано {count}", other: "Выбрано {count}" },
    seasons: "Сезонные цены",
    seasonsHint: "Ночь внутри сезона стоит его цену, каждый год. Сезон может переходить через Новый год; сезоны не должны пересекаться.",
    addSeason: "Добавить сезон",
    seasonTitle: "Сезон {number}",
    seasonName: "Название",
    seasonNamePlaceholder: "Например: Лето",
    from: "С",
    to: "По",
    day: "День",
    month: "Месяц",
    seasonRate: "За ночь, {currency}",
    removeSeason: "Удалить сезон {number}",
    noSeasons: "Сезонов нет: каждая ночь стоит обычную цену за ночь.",
    performedBy: "Выполняют: {names}",
    roomsList: "Номера: {names}",
    breakValue: "+{count} мин перерыв",
    perNight: "{price} за ночь",
    seasonsValue: { one: "{count} сезон", few: "{count} сезона", many: "{count} сезонов", other: "{count} сезона" },
    errors: {
      bufferRange: "От 0 до 240 минут",
      seasonDate: "В этом месяце нет такого дня",
      seasonOverlap: "У сезонов {first} и {second} общие дни: у ночи должна быть одна цена.",
      tooManySeasons: {
        one: "Не больше {count} сезона",
        few: "Не больше {count} сезонов",
        many: "Не больше {count} сезонов",
        other: "Не больше {count} сезона",
      },
    },
  },
};
