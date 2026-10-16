"""
The notice an owner gets about a change of the sub-processor list (DPA
section 8.3), in the owner's cabinet language (Georgian, Russian or
English; others read English). The first line is the e-mail's subject.
"""

from dataclasses import dataclass

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.legal import SubprocessorChangeKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.legal import SubprocessorChange, SubprocessorEntry
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.legal.subprocessor_table import table_language


@dataclass(frozen=True)
class NoticeFrame:
    """The platform's lines of a sub-processor notice in one language."""

    added_subject: str
    removed_subject: str
    added_intro: str
    added_late_intro: str
    removed_intro: str
    details: str
    objection: str
    closing: str


NOTICE_FRAMES: dict[str, NoticeFrame] = {
    "en": NoticeFrame(
        added_subject="New sub-processor from {day}: {name}",
        removed_subject="Sub-processor leaving on {day}: {name}",
        added_intro=(
            "Under section 8.3 of the data processing agreement we let you know "
            "in advance: from {day} Assistant Workshop will also use this "
            "sub-processor for the data of {business}."
        ),
        added_late_intro=(
            "Under section 8.3 of the data processing agreement we should have "
            "told you earlier: since {day} Assistant Workshop also uses this "
            "sub-processor for the data of {business}."
        ),
        removed_intro=(
            "From {day} Assistant Workshop no longer uses this sub-processor for "
            "the data of {business}. Nothing is needed from you."
        ),
        details=(
            "{name}\nPurpose: {purpose}\nPersonal data: {data}\nLocation: {location}"
        ),
        objection=(
            "You may object on reasonable data protection grounds through "
            "platform support (Help in the cabinet) before {day}. If we cannot "
            "agree, you may end the subscription before the change takes effect."
        ),
        closing=(
            "The full list is in section 8 of the agreement: Settings, Data protection."
        ),
    ),
    "ru": NoticeFrame(
        added_subject="Новый субобработчик с {day}: {name}",
        removed_subject="Субобработчик уходит {day}: {name}",
        added_intro=(
            "По пункту 8.3 соглашения об обработке данных сообщаем заранее: с "
            "{day} «Мастерская ассистентов» будет привлекать и этого "
            "субобработчика для данных {business}."
        ),
        added_late_intro=(
            "По пункту 8.3 соглашения об обработке данных мы должны были сообщить "
            "раньше: с {day} «Мастерская ассистентов» привлекает и этого "
            "субобработчика для данных {business}."
        ),
        removed_intro=(
            "С {day} «Мастерская ассистентов» больше не привлекает этого "
            "субобработчика для данных {business}. От вас ничего не требуется."
        ),
        details=(
            "{name}\nЦель: {purpose}\nПерсональные данные: {data}\nГде: {location}"
        ),
        objection=(
            "Вы можете возразить по обоснованным причинам защиты данных через "
            "поддержку платформы («Помощь» в кабинете) до {day}. Если мы не "
            "договоримся, вы можете прекратить подписку до вступления изменения в "
            "силу."
        ),
        closing=(
            "Полный список — в разделе 8 соглашения: «Настройки», «Защита данных»."
        ),
    ),
    "ka": NoticeFrame(
        added_subject="ახალი ქვე-უფლებამოსილი პირი {day}-დან: {name}",
        removed_subject="ქვე-უფლებამოსილი პირი გადის {day}-ს: {name}",
        added_intro=(
            "მონაცემთა დამუშავების შეთანხმების 8.3 პუნქტის შესაბამისად წინასწარ "
            "გაცნობებთ: {day}-დან „ასისტენტების სახელოსნო“ {business}-ის "
            "მონაცემებისთვის ამ ქვე-უფლებამოსილ პირსაც ჩართავს."
        ),
        added_late_intro=(
            "მონაცემთა დამუშავების შეთანხმების 8.3 პუნქტის შესაბამისად ეს უფრო "
            "ადრე უნდა გვეცნობებინა: {day}-დან „ასისტენტების სახელოსნო“ "
            "{business}-ის მონაცემებისთვის ამ ქვე-უფლებამოსილ პირსაც იყენებს."
        ),
        removed_intro=(
            "{day}-დან „ასისტენტების სახელოსნო“ {business}-ის მონაცემებისთვის ამ "
            "ქვე-უფლებამოსილ პირს აღარ იყენებს. თქვენგან არაფერია საჭირო."
        ),
        details=(
            "{name}\nმიზანი: {purpose}\nპერსონალური მონაცემები: {data}\n"
            "ადგილმდებარეობა: {location}"
        ),
        objection=(
            "შეგიძლიათ მონაცემთა დაცვის საფუძვლიანი მიზეზით შეეწინააღმდეგოთ "
            "პლატფორმის მხარდაჭერის მეშვეობით (კაბინეტში „დახმარება“) {day}-მდე. "
            "თუ ვერ შევთანხმდებით, შეგიძლიათ გამოწერა ცვლილების ძალაში შესვლამდე "
            "შეწყვიტოთ."
        ),
        closing=(
            "სრული სია შეთანხმების მე-8 ნაწილშია: „პარამეტრები“, „მონაცემთა დაცვა“."
        ),
    ),
}


def compose_subprocessor_notice(
    change: SubprocessorChange,
    entry: SubprocessorEntry,
    business: BusinessDocument,
    language: LanguageTag,
    is_late: bool,
    resolver: LocalizedTextResolverContract,
) -> MessageText:
    """The whole notice in the owner's language; its first line is the subject."""

    written_in: LanguageTag = table_language(language)
    frame: NoticeFrame = NOTICE_FRAMES[str(written_in)]
    day: str = str(change.effective_on)
    name: str = str(resolver.resolve(entry.name, written_in))
    details: str = frame.details.format(
        name=name,
        purpose=resolver.resolve(entry.purpose, written_in),
        data=resolver.resolve(entry.personal_data, written_in),
        location=resolver.resolve(entry.location, written_in),
    )
    if change.kind is SubprocessorChangeKind.REMOVED:
        lines: list[str] = [
            frame.removed_subject.format(day=day, name=name),
            frame.removed_intro.format(day=day, business=business.name),
            details,
            frame.closing,
        ]
    else:
        intro: str = frame.added_late_intro if is_late else frame.added_intro
        lines = [
            frame.added_subject.format(day=day, name=name),
            intro.format(day=day, business=business.name),
            details,
            *([] if is_late else [frame.objection.format(day=day)]),
            frame.closing,
        ]

    return MessageText("\n\n".join(lines))
