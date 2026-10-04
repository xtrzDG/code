/** `sources.*` texts: «Откуда пришли клиенты» в отчётах и метка источника во входящих, на русском. */

import type { Translation } from "../../../translate";
import type { sourcesEn } from "./sources.en";

export const sourcesRu: Translation<typeof sourcesEn> = {
  title: "Откуда пришли клиенты",
  description: "Разговоры, брони и сколько они стоят — по каждой ссылке, QR-коду, рекламе и номеру телефона.",
  periodLabel: "Период",
  periods: {
    "7d": "7 дней",
    "30d": "30 дней",
    "90d": "90 дней",
  },
  caption: "Клиенты по источникам, {range}",
  columns: {
    source: "Источник",
    conversations: "Разговоры",
    bookings: "Брони",
    requests: "Заявки",
    value: "Стоимость",
  },
  untagged: "Без метки",
  other: {
    one: "Ещё {count} метка",
    few: "Ещё {count} метки",
    many: "Ещё {count} меток",
    other: "Ещё {count} метки",
  },
  phone: "Звонок на {number}",
  ad: "Реклама",
  adWithId: "Реклама {id}",
  total: "Итого",
  noValue: "—",
  share: "{percent} разговоров",
  empty: {
    title: "В этом периоде разговоров не было",
    description: "Источники появятся, когда клиенты напишут или позвонят.",
  },
  tagHint: "Дайте каждой ссылке и QR-коду свою метку в «Каналы» → «Поделиться» — и здесь у них будет своя строка.",
  tagLink: "Поставить метки",
  loading: "Загружаем источники…",
  chip: "Откуда: {source}",
};
