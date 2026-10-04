import type { Translation } from "../../translate";
import type { onboardingEn } from "./en";
import { profileEditRu } from "./profileEdit.ru";

/** Тексты профиля бизнеса. Ключи — как в en.ts. */
export const onboardingRu: Translation<typeof onboardingEn> = {
  onboarding: {
    choose: "Выберите…",
    gaps: {
      times: { one: "{count} раз", few: "{count} раза", many: "{count} раз", other: "{count} раза" },
      notReady: {
        one: "Не хватает {count} обязательного пункта",
        few: "Не хватает {count} обязательных пунктов",
        many: "Не хватает {count} обязательных пунктов",
        other: "Не хватает {count} обязательного пункта",
      },
    },
    week: {
      closed: "Выходной",
      opens: "Открытие",
      closes: "Закрытие",
      addInterval: "Добавить перерыв или вторую смену",
      removeInterval: "Убрать интервал",
      overnight: "до {time} следующего дня",
      roundTheClock: "Круглосуточно",
      copyToAll: "Скопировать понедельник на все дни",
    },
    offer: {
      kinds: {
        faq: "Вопрос и ответ",
        policy: "Правило",
        menu_item: "Блюдо",
        service: "Услуга",
        room_type: "Тип номера",
        package: "Пакет",
        vehicle: "Автомобиль",
        product: "Товар",
      },
    },
    booking: {
      noBookings: "Ваша ниша не принимает брони: помощник собирает заявки и передаёт их менеджеру.",
      resourceKinds: {
        table: "Стол",
        room: "Номер",
        staff: "Специалист",
        arena: "Арена или зал",
        bay: "Пост",
        vehicle: "Автомобиль",
        slot: "Слот времени",
      },
    },
    resources: {
      namePlaceholder: "Например: Арена 1",
    },
  },
  profileEdit: profileEditRu,
};
