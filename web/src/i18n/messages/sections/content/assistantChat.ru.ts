/** `assistant.*` texts of the test chat, in Russian. */

import type { Translation } from "../../../translate";
import type { assistantChatEn } from "./assistantChat.en";

export const assistantChatRu: Translation<typeof assistantChatEn> = {
  chat: {
    newConversation: "Новый разговор",
    logLabel: "Тестовый разговор",
    emptyTitle: "Начните тестовый разговор",
    emptyDescription: "Спросите то, что спрашивают ваши клиенты, на любом языке. Или попробуйте:",
    suggestions: {
      hours: "Во сколько вы работаете?",
      price: "Сколько это стоит?",
      booking: "Хочу забронировать на завтра в 19:00 на 4 человек",
      human: "Можно поговорить с человеком?",
    },
    typing: "Помощник пишет…",
    inputLabel: "Сообщение",
    placeholder: "Напишите сообщение…",
    inputHint: {
      one: "Enter — отправить, Shift+Enter — новая строка. До {count} символа.",
      few: "Enter — отправить, Shift+Enter — новая строка. До {count} символов.",
      many: "Enter — отправить, Shift+Enter — новая строка. До {count} символов.",
      other: "Enter — отправить, Shift+Enter — новая строка. До {count} символа.",
    },
    send: "Отправить",
    failed: "Не отправлено.",
    silent: "Помощник молчит: разговор передан человеку.",
    handedOffTitle: "Передано человеку",
    handedOffDescription: "В настоящем чате сейчас ответил бы ваш сотрудник, поэтому помощник молчит. Начните новый разговор, чтобы продолжить проверку.",
    guardRewritten: "Цифры проверены и исправлены",
    guardHandedOff: "Передано: не уверен в цифре",
    handedOff: "Передано человеку",
    bookingsCreated: {
      one: "Создана тестовая бронь",
      few: "Создано {count} тестовые брони",
      many: "Создано {count} тестовых броней",
      other: "Создано {count} тестовой брони",
    },
    leadsCreated: {
      one: "Создана тестовая заявка",
      few: "Создано {count} тестовые заявки",
      many: "Создано {count} тестовых заявок",
      other: "Создано {count} тестовой заявки",
    },
    toolCalls: {
      one: "{count} вызов инструмента",
      few: "{count} вызова инструментов",
      many: "{count} вызовов инструментов",
      other: "{count} вызова инструментов",
    },
    toolError: "Ошибка",
    toolInput: "Входные данные",
    toolResult: "Результат",
    noVersionsTitle: "Пока нечего проверять",
    noVersionsDescription: "Примените изменения, чтобы подготовить первое обновление помощника, и поговорите с ним здесь.",
    errors: {
      service: "Языковая модель сейчас недоступна. Попробуйте через минуту.",
    },
  },
};
