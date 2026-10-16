/**
 * `quality.*` texts of production quality: the nightly judge's scores of
 * real conversations on the admin client page and on a conversation's
 * card, in Russian.
 */

import type { Translation } from "../../../translate";
import type { qualityEn } from "./quality.en";

export const qualityRu: Translation<typeof qualityEn> = {
  admin: {
    title: "Качество разговоров, 30 дней",
    description: "Каждую ночь ИИ-судья оценивает небольшую выборку реальных разговоров по пяти критериям проверок. Только оценки, без текста клиентов.",
    empty: "За последние 30 дней ни один разговор не оценивался.",
    average: "Среднее за 30 дней",
    lastWeek: "Последние 7 дней",
    previousWeek: "7 дней до этого: {score}",
    judged: "Оценено разговоров",
    dropping: "Ниже на {percent}%",
    droppingNote: "Последняя неделя оценена на {percent}% ниже предыдущей. Посмотрите худшие разговоры ниже и последнее обновление клиента.",
    scoreValue: "{score} / 5",
    trendLabel: "Средняя оценка по дням за последние 30 дней",
    noScoresDay: "{date}: не оценивались",
    dayValue: "{date}: {score} / 5, разговоров: {count}",
    showTable: "Показать таблицей",
    day: "День",
    count: "Оценено",
    lowestTitle: "Разговоры с самой низкой оценкой",
    lowestCaption: "Пять самых низких оценок за 30 дней",
    judgedAt: "Оценён",
    channel: "Канал",
    language: "Язык",
    score: "Оценка",
    weak: "Слабые места",
    noWeak: "Ниже 4 нет",
  },
  conversation: {
    title: "Оценка ИИ-судьи",
    description: "Этот разговор попал в ночную выборку для оценки качества.",
    judgedAt: "Оценён {date}",
    notes: "Замечания",
  },
};
