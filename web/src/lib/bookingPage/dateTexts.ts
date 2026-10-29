/**
 * Texts of the date field on a guest's booking page (/r/{token}): the UI
 * kit's DateField and its calendar speak the page's language there
 * (DateFieldLanguage), not the cabinet's, in every language of the written
 * confirmation (texts.ts); English is the fallback.
 */

import { primaryLanguage } from "../hostedChat/language";

export interface BookingDateTexts {
  placeholder: string;
  open: string;
  calendar: string;
  previousMonth: string;
  nextMonth: string;
  today: string;
  clear: string;
  /** Under the field when the date typed is before the business's today. */
  pastDate: string;
}

const row = (...texts: [string, string, string, string, string, string, string, string]): BookingDateTexts => {
  const [placeholder, open, calendar, previousMonth, nextMonth, today, clear, pastDate] = texts;
  return { placeholder, open, calendar, previousMonth, nextMonth, today, clear, pastDate };
};

// placeholder, open, calendar, previous month, next month, today, clear, a date before today
export const BOOKING_DATE_TEXTS: Readonly<Record<string, BookingDateTexts>> = {
  en: row("Choose a date", "Open the calendar", "Calendar", "Previous month", "Next month", "Today", "Clear", "Choose today or a later date."),
  de: row("Datum wählen", "Kalender öffnen", "Kalender", "Vorheriger Monat", "Nächster Monat", "Heute", "Löschen", "Wählen Sie heute oder einen späteren Tag."),
  fr: row("Choisir une date", "Ouvrir le calendrier", "Calendrier", "Mois précédent", "Mois suivant", "Aujourd’hui", "Effacer", "Choisissez aujourd’hui ou une date ultérieure."),
  es: row("Elige una fecha", "Abrir el calendario", "Calendario", "Mes anterior", "Mes siguiente", "Hoy", "Borrar", "Elige hoy o una fecha posterior."),
  it: row("Scegli una data", "Apri il calendario", "Calendario", "Mese precedente", "Mese successivo", "Oggi", "Cancella", "Scegli oggi o una data successiva."),
  pt: row("Escolha uma data", "Abrir o calendário", "Calendário", "Mês anterior", "Próximo mês", "Hoje", "Limpar", "Escolha hoje ou uma data posterior."),
  pl: row("Wybierz datę", "Otwórz kalendarz", "Kalendarz", "Poprzedni miesiąc", "Następny miesiąc", "Dzisiaj", "Wyczyść", "Wybierz dzisiejszą lub późniejszą datę."),
  tr: row("Bir tarih seçin", "Takvimi aç", "Takvim", "Önceki ay", "Sonraki ay", "Bugün", "Temizle", "Bugünü veya daha sonraki bir tarihi seçin."),
  ru: row("Выберите дату", "Открыть календарь", "Календарь", "Предыдущий месяц", "Следующий месяц", "Сегодня", "Очистить", "Выберите сегодняшний или более поздний день."),
  uk: row("Оберіть дату", "Відкрити календар", "Календар", "Попередній місяць", "Наступний місяць", "Сьогодні", "Очистити", "Оберіть сьогоднішній або пізніший день."),
  kk: row("Күнді таңдаңыз", "Күнтізбені ашу", "Күнтізбе", "Алдыңғы ай", "Келесі ай", "Бүгін", "Тазалау", "Бүгінгі немесе кейінгі күнді таңдаңыз."),
  ka: row("აირჩიეთ თარიღი", "კალენდრის გახსნა", "კალენდარი", "წინა თვე", "შემდეგი თვე", "დღეს", "გასუფთავება", "აირჩიეთ დღევანდელი ან უფრო გვიანი თარიღი."),
  hy: row("Ընտրեք ամսաթիվ", "Բացել օրացույցը", "Օրացույց", "Նախորդ ամիս", "Հաջորդ ամիս", "Այսօր", "Մաքրել", "Ընտրեք այսօրվա կամ ավելի ուշ ամսաթիվ։"),
  he: row("בחרו תאריך", "פתיחת לוח השנה", "לוח שנה", "החודש הקודם", "החודש הבא", "היום", "ניקוי", "בחרו את היום או תאריך מאוחר יותר."),
  ar: row("اختر تاريخًا", "فتح التقويم", "التقويم", "الشهر السابق", "الشهر التالي", "اليوم", "مسح", "اختر اليوم أو تاريخًا لاحقًا."),
};

/** The date field's texts in a language tag ("pt-BR" uses "pt"); English when there are none. */
export function bookingDateTexts(tag: string): BookingDateTexts {
  return BOOKING_DATE_TEXTS[primaryLanguage(tag)] ?? (BOOKING_DATE_TEXTS.en as BookingDateTexts);
}
