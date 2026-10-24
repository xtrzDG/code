"""
The breach notice an owner gets (DPA section 12.1), in the owner's cabinet
language (Georgian, Russian or English; others read English). The frame is
the platform's; the five texts are what the team wrote for the incident in
that language, else in English. Times are in the business's time zone.
"""

from dataclasses import dataclass
from datetime import datetime

from typed_time_provider import Microseconds

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.incidents import IncidentDocument, IncidentNoticeText
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000
FALLBACK_LANGUAGE: str = "en"


@dataclass(frozen=True)
class NoticeFrame:
    """The platform's own lines of the notice in one language."""

    subject: str
    intro: str
    incident: str
    timeline: str
    nature: str
    subjects: str
    records: str
    consequences: str
    measures: str
    closing: str


NOTICE_FRAMES: dict[str, NoticeFrame] = {
    "en": NoticeFrame(
        subject="Personal data breach notice: {business}",
        intro=(
            "Under section 12.1 of the data processing agreement we inform you "
            "of a personal data breach affecting your business's data in "
            "Assistant Workshop."
        ),
        incident="Incident: {title} (reference {reference})",
        timeline="It began {started}; we became aware of it {detected}.",
        nature="What happened: {text}",
        subjects="People concerned: {text}, about {count}",
        records="Records concerned: {text}, about {count}",
        consequences="Likely consequences: {text}",
        measures="Measures taken or proposed: {text}",
        closing=(
            "We will keep you informed and, where required, help you notify "
            "the supervisory authority and the people concerned (section 12.2)."
        ),
    ),
    "ru": NoticeFrame(
        subject="Уведомление о нарушении безопасности персональных данных: {business}",
        intro=(
            "По пункту 12.1 соглашения об обработке данных сообщаем вам о "
            "нарушении безопасности персональных данных, затронувшем данные "
            "вашего бизнеса в «Мастерской ассистентов»."
        ),
        incident="Инцидент: {title} (номер {reference})",
        timeline="Начало: {started}; мы узнали о нём: {detected}.",
        nature="Что произошло: {text}",
        subjects="Затронутые люди: {text}, примерно {count}",
        records="Затронутые записи: {text}, примерно {count}",
        consequences="Вероятные последствия: {text}",
        measures="Принятые или предлагаемые меры: {text}",
        closing=(
            "Мы будем сообщать вам новые сведения и, если это требуется, "
            "поможем уведомить надзорный орган и затронутых людей (пункт 12.2)."
        ),
    ),
    "ka": NoticeFrame(
        subject=(
            "შეტყობინება პერსონალურ მონაცემთა უსაფრთხოების ინციდენტის შესახებ: "
            "{business}"
        ),
        intro=(
            "მონაცემთა დამუშავების შეთანხმების 12.1 პუნქტის შესაბამისად "
            "გაცნობებთ პერსონალურ მონაცემთა უსაფრთხოების ინციდენტის შესახებ, "
            "რომელიც ეხება თქვენი ბიზნესის მონაცემებს „ასისტენტების "
            "სახელოსნოში“."
        ),
        incident="ინციდენტი: {title} (ნომერი {reference})",
        timeline="დაიწყო: {started}; ჩვენთვის ცნობილი გახდა: {detected}.",
        nature="რა მოხდა: {text}",
        subjects="შეხებული პირები: {text}, დაახლოებით {count}",
        records="შეხებული ჩანაწერები: {text}, დაახლოებით {count}",
        consequences="შესაძლო შედეგები: {text}",
        measures="მიღებული ან შემოთავაზებული ზომები: {text}",
        closing=(
            "გაცნობებთ ახალ ინფორმაციას და, საჭიროების შემთხვევაში, "
            "დაგეხმარებით საზედამხედველო ორგანოსა და შეხებული პირების "
            "ინფორმირებაში (პუნქტი 12.2)."
        ),
    ),
}


def notice_language(language: LanguageTag) -> str:
    """The frame language for a cabinet language: its base, if there is a frame."""

    base: str = str(language).split("-")[0]
    return base if base in NOTICE_FRAMES else FALLBACK_LANGUAGE


def pick_notice_text(
    incident: IncidentDocument, language: LanguageTag
) -> IncidentNoticeText:
    """The incident's texts in the owner's language, else the English ones."""

    by_language: dict[str, IncidentNoticeText] = {
        str(text.language).split("-")[0]: text for text in incident.notice_texts
    }
    return by_language.get(notice_language(language), by_language[FALLBACK_LANGUAGE])


def compose_breach_notice(
    incident: IncidentDocument,
    business: BusinessDocument,
    language: LanguageTag,
) -> MessageText:
    """The whole notice; its first line is the e-mail subject."""

    frame: NoticeFrame = NOTICE_FRAMES[notice_language(language)]
    texts: IncidentNoticeText = pick_notice_text(incident, language)
    lines: list[str] = [
        frame.subject.format(business=business.name),
        frame.intro,
        frame.incident.format(title=incident.title, reference=incident.id),
        frame.timeline.format(
            started=local_time(incident.started_at, business),
            detected=local_time(incident.detected_at, business),
        ),
        frame.nature.format(text=texts.nature),
        frame.subjects.format(
            text=texts.subject_categories,
            count=int(incident.approximate_subject_count or 0),
        ),
        frame.records.format(
            text=texts.record_categories,
            count=int(incident.approximate_record_count or 0),
        ),
        frame.consequences.format(text=texts.likely_consequences),
        frame.measures.format(text=texts.measures),
        frame.closing,
    ]
    return MessageText("\n\n".join(lines))


def local_time(moment: Microseconds, business: BusinessDocument) -> str:
    """A moment in the business's time zone, to the minute, with the zone."""

    zone = load_time_zone(business.timezone)
    local: datetime = datetime.fromtimestamp(
        int(moment) / MICROSECONDS_PER_SECOND, tz=zone
    )
    return f"{local.strftime('%Y-%m-%d %H:%M')} ({business.timezone})"
