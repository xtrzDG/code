/** `legalPages.*`: публичные юридические страницы и контакты, по-русски. */

import type { Translation } from "../../../translate";
import type { legalPagesEn } from "./legalPages.en";

export const legalPagesRu: Translation<typeof legalPagesEn> = {
  nav: {
    terms: "Условия использования",
    privacy: "Политика конфиденциальности",
    dpa: "Соглашение об обработке данных",
    security: "Безопасность",
    contact: "Контакты",
  },
  footerLabel: "Документы и контакты",
  draftTitle: "Черновик",
  draftText: "Юрист ещё не проверил этот текст, а поля в квадратных скобках ещё предстоит заполнить. Мы публикуем его, чтобы вы видели, что предлагает сервис; в таком виде он пока не действует.",
  document: {
    upcoming: "С {date} действует новая версия; она уже опубликована.",
    otherLanguage: "На вашем языке этого текста пока нет; он показан на языке: {language}.",
  },
  unavailable: "Сейчас не удалось загрузить текст. Попробуйте позже.",
  dpaLead: "Каждый бизнес на платформе принимает этот договор в кабинете перед запуском; в нём сказано, как данные клиентов обрабатываются по поручению бизнеса.",
  related: "Другие документы",
  contactTitle: "Контакты",
  contactLead: "Кто предоставляет сервис и как связаться с человеком.",
  operatorTitle: "Оператор",
  legalName: "Название",
  address: "Адрес",
  taxId: "Налоговый номер",
  country: "Страна",
  email: "E-mail",
  operatorMissing: "Адрес и регистрационные данные оператора появятся здесь до того, как сервис откроется для клиентов.",
  supportTitle: "Напишите нам",
  supportWhatsApp: "WhatsApp",
  supportTelegram: "Telegram",
  supportEmail: "E-mail",
  supportMissing: "Контакты поддержки появятся здесь до того, как сервис откроется для клиентов.",
  securityReportTitle: "Нашли уязвимость?",
  securityReportText: "Пожалуйста, сообщите о ней приватно; как это сделать, написано в нашем security.txt.",
  securityReportLink: "Открыть правила для исследователей безопасности",
};
