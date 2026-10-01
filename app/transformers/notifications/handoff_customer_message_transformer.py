from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.operations import HandoffCustomerMessageInput
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.message_rendering import (
    describe_date,
    localized,
    render,
)
from app.utilities.scheduling.localized_formatting import choose_template_language

REPLY_SOON: LocalizedText = localized(
    en="Your request has been passed to a colleague. They will reply soon.",
    ru="Ваш вопрос передан коллеге. Вам скоро ответят.",
    ka="თქვენი მოთხოვნა კოლეგას გადაეცა. მალე გიპასუხებენ.",
    tr="Talebiniz bir çalışma arkadaşımıza iletildi. Size kısa süre içinde "
    "dönüş yapılacak.",
    he="הפנייה שלך הועברה לעמית. יחזרו אליך בקרוב.",
    ar="تم تحويل طلبك إلى أحد الزملاء. سيتم الرد عليك قريبًا.",
    hy="Ձեր հարցումը փոխանցվել է գործընկերոջը։ Շուտով կպատասխանեն։",
    uk="Ваше питання передано колезі. Вам незабаром дадуть відповідь.",
    de="Ihre Anfrage wurde an einen Kollegen weitergegeben. Sie erhalten bald "
    "eine Antwort.",
    fr="Votre demande a été transmise à un collègue. Vous aurez une réponse bientôt.",
    es="Su consulta se ha pasado a un compañero. Le responderán pronto.",
    it="La sua richiesta è stata inoltrata a un collega. Le risponderà a breve.",
)

REPLY_WHEN_OPEN: LocalizedText = localized(
    en="Your request has been passed to a colleague. We are closed now; they "
    "will reply when we open: {date}, {time}.",
    ru="Ваш вопрос передан коллеге. Сейчас мы закрыты — вам ответят, когда "
    "откроемся: {date}, {time}.",
    ka="თქვენი მოთხოვნა კოლეგას გადაეცა. ახლა დაკეტილი ვართ — გიპასუხებენ, "
    "როცა გავიხსნებით: {date}, {time}.",
    tr="Talebiniz bir çalışma arkadaşımıza iletildi. Şu anda kapalıyız; "
    "açıldığımızda size dönüş yapılacak: {date}, {time}.",
    he="הפנייה שלך הועברה לעמית. כרגע אנחנו סגורים; יחזרו אליך כשנפתח: {date}, {time}.",
    ar="تم تحويل طلبك إلى أحد الزملاء. نحن مغلقون الآن؛ سيتم الرد عليك عند "
    "افتتاحنا: {date}، {time}.",
    hy="Ձեր հարցումը փոխանցվել է գործընկերոջը։ Հիմա փակ ենք․ կպատասխանեն, "
    "երբ բացվենք՝ {date}, {time}։",
    uk="Ваше питання передано колезі. Зараз ми зачинені — вам відповідять, "
    "коли відкриємося: {date}, {time}.",
    de="Ihre Anfrage wurde an einen Kollegen weitergegeben. Wir haben gerade "
    "geschlossen; Sie erhalten eine Antwort, sobald wir öffnen: {date}, {time}.",
    fr="Votre demande a été transmise à un collègue. Nous sommes fermés pour le "
    "moment ; vous aurez une réponse à notre ouverture : {date}, {time}.",
    es="Su consulta se ha pasado a un compañero. Ahora estamos cerrados; le "
    "responderán cuando abramos: {date}, {time}.",
    it="La sua richiesta è stata inoltrata a un collega. Ora siamo chiusi; le "
    "risponderanno all'apertura: {date}, {time}.",
)


class HandoffCustomerMessageTransformer(
    TransformerContract[HandoffCustomerMessageInput, MessageText]
):
    """
    What the assistant tells the customer after a handoff (concept: "a
    colleague will reply soon" during opening hours; outside them, a reply
    when the business opens, with the local opening date and time).
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: HandoffCustomerMessageInput) -> MessageText:
        if input_data.reopens_on is None or input_data.reopens_at is None:
            language: LanguageTag = choose_template_language(
                REPLY_SOON, input_data.language
            )
            return MessageText(render(self._text_resolver, REPLY_SOON, language, {}))

        language = choose_template_language(REPLY_WHEN_OPEN, input_data.language)
        return MessageText(
            render(
                self._text_resolver,
                REPLY_WHEN_OPEN,
                language,
                {
                    "date": describe_date(input_data.reopens_on, language),
                    "time": str(input_data.reopens_at),
                },
            )
        )
