/** `knowledge.aliases.*` на русском: названия позиции на других языках бизнеса, чипы в редакторе знаний. */

import type { Translation } from "../../../translate";
import type { knowledgeAliasesEn } from "./knowledgeAliases.en";

export const knowledgeAliasesRu: Translation<typeof knowledgeAliasesEn> = {
  aliases: {
    title: "Названия на других языках",
    hint: "Клиенты спрашивают на своём языке. Эти названия ищутся так же, как заголовок, а одобренные вами становятся готовыми вопросами в чате на сайте.",
    listLabel: "Названия: {language}",
    none: "Пока нет названия ({language})",
    suggested: "Предложено",
    suggestedHint: "Предложенные названия уже участвуют в поиске, но клиенты увидят их только после вашего одобрения.",
    accept: "Одобрить «{text}»",
    remove: "Удалить «{text}»",
    addLabel: "Добавить название ({language})",
    placeholder: "Название ({language})",
    add: "Добавить",
    tooLong: "Название — не длиннее 200 символов",
    duplicate: "Такое название уже есть в списке",
    tooMany: "Не больше трёх названий на язык",
    suggest: "Предложить переводы",
    suggesting: "Подбираем…",
    saveTitleFirst: "Сначала сохраните новый заголовок, потом запросите переводы.",
    suggestedCount: {
      one: "Предложено {count} название — проверьте его ниже",
      few: "Предложено {count} названия — проверьте их ниже",
      many: "Предложено {count} названий — проверьте их ниже",
      other: "Предложено {count} названия — проверьте их ниже",
    },
    nothingSuggested: "Предлагать нечего: на каждом языке название уже есть.",
  },
};
