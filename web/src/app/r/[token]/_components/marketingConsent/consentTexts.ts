/**
 * The marketing box of a guest's booking page, in every language of the
 * page (lib/bookingPage/texts.ts). The wording is a legal text: the
 * version the guest saw is stored with their consent
 * (`MARKETING_CONSENT_TEXT_VERSION`, the API's MarketingConsentText), so a
 * changed wording is a new version on both sides. Each text names the STOP
 * word of its language, as the campaign messages do. `{business}` is
 * filled in.
 */

import { primaryLanguage } from "@/lib/hostedChat/language";

export const MARKETING_CONSENT_TEXT_VERSION = "2026-11-02";

export interface MarketingConsentTexts {
  /** The consent itself, the checkbox's label. */
  label: string;
  /** That it is optional and how to take it back. */
  note: string;
  /** The choice could not be saved (the box shows what is stored). */
  failed: string;
}

export const MARKETING_CONSENT_TEXTS: Readonly<Record<string, MarketingConsentTexts>> = {
  en: {
    label: "I'd like to get news, offers and invitations to come back from {business} in the chat where I made this booking.",
    note: "Optional. You can untick it at any time, or reply STOP in that chat.",
    failed: "Your choice was not saved. Please try again.",
  },
  it: {
    label: "Desidero ricevere da {business} novità, offerte e inviti a tornare nella chat in cui ho fatto questa prenotazione.",
    note: "Facoltativo. Puoi togliere la spunta in qualsiasi momento o rispondere STOP in quella chat.",
    failed: "La tua scelta non è stata salvata. Riprova.",
  },
  de: {
    label: "Ich möchte von {business} Neuigkeiten, Angebote und Einladungen zu einem erneuten Besuch in dem Chat erhalten, in dem ich diese Buchung gemacht habe.",
    note: "Freiwillig. Sie können das Häkchen jederzeit entfernen oder in diesem Chat mit STOPP antworten.",
    failed: "Ihre Auswahl wurde nicht gespeichert. Bitte versuchen Sie es erneut.",
  },
  fr: {
    label: "Je souhaite recevoir de {business} des nouvelles, des offres et des invitations à revenir dans la conversation où j'ai fait cette réservation.",
    note: "Facultatif. Vous pouvez décocher la case à tout moment ou répondre STOP dans cette conversation.",
    failed: "Votre choix n'a pas été enregistré. Veuillez réessayer.",
  },
  es: {
    label: "Quiero recibir de {business} novedades, ofertas e invitaciones para volver en el chat donde hice esta reserva.",
    note: "Opcional. Puedes desmarcarlo en cualquier momento o responder STOP en ese chat.",
    failed: "Tu elección no se ha guardado. Inténtalo de nuevo.",
  },
  pt: {
    label: "Quero receber de {business} novidades, ofertas e convites para voltar na conversa em que fiz esta reserva.",
    note: "Opcional. Pode desmarcar a qualquer momento ou responder PARAR nessa conversa.",
    failed: "A sua escolha não foi guardada. Tente novamente.",
  },
  pl: {
    label: "Chcę otrzymywać od {business} nowości, oferty i zaproszenia do ponownej wizyty na czacie, w którym złożono tę rezerwację.",
    note: "Dobrowolne. Możesz w każdej chwili odznaczyć to pole lub odpisać STOP na tym czacie.",
    failed: "Twój wybór nie został zapisany. Spróbuj ponownie.",
  },
  tr: {
    label: "{business} işletmesinden bu rezervasyonu yaptığım sohbette haberler, teklifler ve tekrar gelme davetleri almak istiyorum.",
    note: "İsteğe bağlı. İşareti istediğiniz zaman kaldırabilir veya o sohbette DUR yazabilirsiniz.",
    failed: "Seçiminiz kaydedilmedi. Lütfen tekrar deneyin.",
  },
  ru: {
    label: "Я хочу получать от {business} новости, предложения и приглашения прийти снова в чате, где сделано это бронирование.",
    note: "Необязательно. Снять отметку можно в любой момент или ответить СТОП в этом чате.",
    failed: "Ваш выбор не сохранён. Попробуйте ещё раз.",
  },
  uk: {
    label: "Я хочу отримувати від {business} новини, пропозиції та запрошення прийти знову в чаті, де зроблено це бронювання.",
    note: "Необов'язково. Зняти позначку можна будь-коли або надіслати СТОП у цьому чаті.",
    failed: "Ваш вибір не збережено. Спробуйте ще раз.",
  },
  kk: {
    label: "Мен {business} жаңалықтарын, ұсыныстарын және қайта келуге шақыруларын осы брондау жасалған чатта алғым келеді.",
    note: "Міндетті емес. Белгіні кез келген уақытта алып тастауға немесе сол чатта СТОП деп жазуға болады.",
    failed: "Таңдауыңыз сақталмады. Қайталап көріңіз.",
  },
  ka: {
    label: "თანახმა ვარ, {business} მომწეროს სიახლეები, შეთავაზებები და ხელახლა მოსვლის მოწვევები იმ ჩატში, სადაც ეს ჯავშანი გაკეთდა.",
    note: "არასავალდებულოა. მონიშვნის მოხსნა ნებისმიერ დროს შეგიძლიათ, ან უპასუხეთ იმავე ჩატში: სტოპ.",
    failed: "თქვენი არჩევანი ვერ შეინახა. სცადეთ ხელახლა.",
  },
  hy: {
    label: "Ցանկանում եմ, որ {business} ինձ ուղարկի նորություններ, առաջարկներ և կրկին այցելելու հրավերներ այն զրույցում, որտեղ կատարվել է այս ամրագրումը։",
    note: "Կամընտիր է։ Նշումը կարող եք հանել ցանկացած պահի կամ այդ զրույցում պատասխանել ՍՏՈՊ։",
    failed: "Ձեր ընտրությունը չպահպանվեց։ Խնդրում ենք կրկին փորձել։",
  },
  he: {
    label: "אשמח לקבל מ-{business} עדכונים, מבצעים והזמנות לחזור בצ'אט שבו בוצעה ההזמנה הזו.",
    note: "לא חובה. אפשר לבטל את הסימון בכל עת או להשיב עצור באותו צ'אט.",
    failed: "הבחירה לא נשמרה. נסו שוב.",
  },
  ar: {
    label: "أرغب في تلقّي الأخبار والعروض ودعوات العودة من {business} في المحادثة التي أجريت فيها هذا الحجز.",
    note: "اختياري. يمكنك إلغاء التحديد في أي وقت أو الرد بكلمة توقف في تلك المحادثة.",
    failed: "لم يُحفظ اختيارك. يُرجى المحاولة مرة أخرى.",
  },
};

const ENGLISH = MARKETING_CONSENT_TEXTS.en as MarketingConsentTexts;

/** The box's texts in a page language ("pt-BR" uses "pt"); English when there are none. */
export function marketingConsentTexts(tag: string): MarketingConsentTexts {
  return MARKETING_CONSENT_TEXTS[primaryLanguage(tag)] ?? ENGLISH;
}
