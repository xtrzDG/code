/** `setup.*` texts: "Create an AI assistant", before the assistant exists, in Russian. */

import type { Translation } from "../../../translate";
import type { setupEn } from "./setup.en";

export const setupRu: Translation<typeof setupEn> = {
  navEntry: "Создать AI-помощника",
  navEntryHint: "Шаг за шагом, около 10 минут",
  eyebrow: "{business}",
  title: "Давайте создадим вашего AI-помощника",
  description:
    "Расскажите о бизнесе в нескольких простых шагах. Мы соберём помощника, который днём и ночью отвечает клиентам, принимает брони и зовёт вас, когда нужен человек.",
  start: "Создать AI-помощника",
  continue: "Продолжить создание",
  progress: "Готово шагов: {done} из {total}",
  duration: "Около 10 минут. Можно прерваться и вернуться в любой момент.",
  stagesLabel: "Как это устроено",
  stages: {
    business: {
      title: "Расскажите о бизнесе",
      description: "Контакты, часы работы и что вы предлагаете.",
    },
    rules: {
      title: "Научите своим правилам",
      description: "Брони, ответы на частые вопросы и когда звать вас.",
    },
    meet: {
      title: "Познакомьтесь с помощником",
      description: "Попробуйте его в чате, затем включите для клиентов.",
    },
  },
  staffTitle: "Помощника создают",
  staffDescription:
    "Владелец «{business}» его настраивает. Разговоры, брони и заявки появятся здесь, как только помощник будет готов.",
  create: "Создать моего помощника",
};
