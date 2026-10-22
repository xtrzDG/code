/**
 * `metaConnect.*` по-русски: «Продолжить с Facebook» для WhatsApp,
 * Instagram и Messenger, выбор страницы, отказы Meta простыми словами,
 * ответы на комментарии в карточке Instagram и карточка Meta в настройке.
 */

import type { Translation } from "../../../translate";
import type { metaConnectEn } from "./metaConnect.en";

export const metaConnectRu: Translation<typeof metaConnectEn> = {
  continue: "Продолжить с Facebook",
  intro: {
    whatsapp:
      "Войдите через Facebook и в его окне выберите или создайте аккаунт WhatsApp Business и номер. Номер мы подключим сами.",
    instagram:
      "Войдите через Facebook и выберите страницу, к которой привязан профессиональный аккаунт Instagram. Подключим сами.",
    messenger: "Войдите через Facebook и выберите страницу, на чаты Messenger которой будет отвечать помощник.",
  },
  orManual: "Уже есть идентификаторы и ключ? Их по-прежнему можно ввести вручную.",
  preparing: "Готовим Facebook…",
  starting: "Начинаем…",
  openWindow: "Открыть окно Facebook",
  openHint: "Браузер просит дождаться нажатия: вход в Facebook откроется в новом окне.",
  waiting: "Завершите вход в окне Facebook. Это окно подождёт.",
  finishing: "Подключаем…",
  notices: {
    cancelled: "Окно Facebook закрылось раньше времени. Попробуйте ещё раз, когда будете готовы.",
    failed: "Facebook не смог завершить подключение. Попробуйте ещё раз или введите данные вручную.",
    unavailable:
      "Вход через Facebook не загрузился (его может блокировать блокировщик рекламы). Попробуйте позже или введите данные вручную.",
  },
  pages: {
    title: "Выберите страницу",
    hint: "Страницы, которыми вы управляете в Facebook.",
    instagramHint: "Подключить Instagram можно только со страницей, к которой привязан профессиональный аккаунт Instagram.",
    none: "Facebook не показал ни одной вашей страницы. Начните заново и отметьте страницу бизнеса в окне Facebook.",
    instagram: "Instagram: @{username}",
    instagramNoName: "Instagram привязан",
    noInstagram: "Instagram не привязан",
    connect: "Подключить эту страницу",
    connecting: "Подключаем…",
  },
  refusals: {
    meta_link_expired: "Этот вход через Facebook уже закончился. Начните заново.",
    meta_not_configured: "Вход через Facebook на этом сервере не настроен. Введите данные вручную.",
    meta_permission_missing: "Facebook выдал не все нужные разрешения. Начните заново и оставьте все галочки.",
    whatsapp_account_missing: "Facebook не вернул аккаунт WhatsApp Business. Начните заново и выберите или создайте его.",
    whatsapp_number_missing: "В этом аккаунте WhatsApp Business ещё нет номера. Добавьте его в окне Facebook.",
    whatsapp_pin_mismatch:
      "На номере включена двухшаговая проверка с другим PIN-кодом. Отключите её в WhatsApp Manager и попробуйте ещё раз.",
    meta_page_not_found: "Facebook не дал доступа к этой странице. Начните заново и отметьте её в окне Facebook.",
    instagram_account_missing:
      "К этой странице не привязан профессиональный аккаунт Instagram. Привяжите его в настройках Instagram или выберите другую страницу.",
  },
  commentReplies: {
    title: "Ответы на комментарии",
    toggle: "Отвечать в Direct на комментарии с ключевым словом",
    description:
      "Когда человек пишет одно из ваших ключевых слов в комментарии под постом, помощник присылает ему одно сообщение в Direct. Не больше одного в день каждому и 60 в час.",
    unavailable: "Ответы на комментарии заработают со следующим обновлением сервиса. До тех пор настройки сохраняются.",
    summaryOn: "Включено, на слова: {keywords}",
    summaryOff: "Выключено",
    keywords: "Ключевые слова",
    keywordsHint: "Слово или короткая фраза; после каждой нажмите Enter. До 20.",
    keywordInput: "Новое ключевое слово",
    addKeyword: "Добавить",
    removeKeyword: "Убрать «{keyword}»",
    replyText: "Сообщение в Direct",
    replyHint: "До 1000 символов. Клиент может ответить, и помощник продолжит разговор.",
    save: "Сохранить",
    saving: "Сохраняем…",
    savedToast: "Ответы на комментарии сохранены",
    errors: {
      keywordsMissing: "Добавьте хотя бы одно ключевое слово",
      replyMissing: "Напишите сообщение",
      keyword: "До 50 символов, в одну строку",
      tooMany: "Не больше 20 ключевых слов",
    },
  },
  tunnel: {
    title: "WhatsApp, Instagram и Messenger",
    text: "Подключите их через свой аккаунт Facebook сейчас или позже на странице «Каналы».",
    connect: "Подключить {channel}",
    connected: "Подключено",
  },
};
