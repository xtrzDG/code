/** `adminAudit.*` по-русски: страница «Аудит» админа платформы. */

import type { Translation } from "../../../translate";
import type { adminAuditEn } from "./adminAudit.en";

export const adminAuditRu: Translation<typeof adminAuditEn> = {
  nav: "Аудит",
  title: "Аудит",
  description: "Ежедневная проверка всех журналов действий на подмену и собственный журнал платформы: неудачные входы, блокировки, выходы и смены ключей.",
  chains: {
    title: "Проверка на подмену",
    platform: "Журнал платформы",
    intact: "Не изменены",
    broken: "Изменены",
    allIntact: "Последние проверки нашли журналы всех бизнесов такими, какими они были записаны.",
    brokenList: "Изменённые журналы",
    business: "Бизнес",
    entry: "Запись",
    problem: "Что не так",
    checked: "Проверено",
    platformName: "Платформа",
  },
  log: {
    title: "Журнал платформы",
    description: "Записи без бизнеса, сначала новые. Адрес, на который ушёл код входа, виден только как ключевой отпечаток, сам адрес — никогда.",
    filters: "Фильтр журнала платформы",
    event: "Событие",
    allEvents: "Все события",
    when: "Когда",
    what: "Что",
    who: "Кто",
    address: "Сетевой адрес",
    entry: "Запись",
    empty: "Записей пока нет",
    emptyFiltered: "Нет записей с этим событием",
    unknownPerson: "Неизвестный человек",
    system: "Система",
  },
  events: {
    login_failed: "Неверный код",
    otp_locked: "Код заблокирован",
    mfa_locked: "Второй шаг заблокирован",
    logout: "Выход",
    key_rotation: "Смена ключа",
  },
  entities: {
    login_destination: "Адрес для входа",
    user: "Человек",
    user_session: "Сеанс",
    encryption_keys: "Ключи шифрования",
    audit_log_entry: "Записи аудита",
  },
};
