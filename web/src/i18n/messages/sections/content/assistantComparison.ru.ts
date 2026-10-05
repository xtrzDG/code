/**
 * `assistant.comparison.*` texts: an update's checks against the live
 * update's, in Russian.
 */

import type { Translation } from "../../../translate";
import type { assistantComparisonEn } from "./assistantComparison.en";

export const assistantComparisonRu: Translation<typeof assistantComparisonEn> = {
  comparison: {
    title: "Сравнение с обновлением {number} в работе",
    description: "Сравниваются только сценарии, которые сыграли оба обновления.",
    shared: "Сравнено сценариев: {count}",
    averageScore: "Средняя оценка",
    averageWas: "В работе: {score}",
    newFailures: "Новые проблемы",
    fixed: "Исправлено",
    newFailuresHint: "Эти сценарии проходили у обновления в работе, а сейчас не проходят.",
    fixedHint: "Эти сценарии не проходили у обновления в работе, а сейчас проходят.",
    scoreDrops: "Оценки снизились",
    scoreRises: "Оценки выросли",
    criteria: "По критериям",
    scenario: "{name} · {language}",
    scoreMove: "{from} → {to}",
    outcomeMove: "Было: {from}, сейчас: {to}",
    noChanges: "По сравнению с обновлением в работе ничего не изменилось: новых проблем нет, ни одна оценка не сдвинулась на полбалла и больше.",
    noShared: "У этого прогона и прогона обновления в работе пока нет общих сценариев.",
    plays: "Пройдено прогонов: {passed} из {played}",
    playsHint: "Важные сценарии играются несколько раз, и пройти нужно каждый раз.",
  },
};
