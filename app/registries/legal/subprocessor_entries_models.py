"""
The sub-processors behind the assistant's answers and calls: the language
models, the voice agent and the record of model calls.
"""

from app.registries.legal.subprocessor_texts import (
    ORIGINAL_LIST_DATE,
    key,
    modules,
    texts,
)
from app.schemas.constants.legal import ProcessorFlow
from app.schemas.dto.legal import SubprocessorEntry
from app.schemas.typings.legal.constrained_strings import SubprocessorChangeDate

# Anthropic as the judge of a sample of real conversations is a new purpose:
# announced to owners on this day (the send_subprocessor_notices job), in
# force 30 days later. Until then the nightly sample is judged by the
# assistant's own provider (QUALITY_SAMPLING_JUDGE_SAME_PROVIDER).
ANTHROPIC_QUALITY_ANNOUNCED_ON: SubprocessorChangeDate = SubprocessorChangeDate(
    "2026-10-06"
)
ANTHROPIC_QUALITY_FROM: SubprocessorChangeDate = SubprocessorChangeDate("2026-11-05")

MODEL_SUBPROCESSORS: tuple[SubprocessorEntry, ...] = (
    SubprocessorEntry(
        key=key("openai"),
        name=texts(
            "OpenAI (EU data residency project)",
            "OpenAI (проект с хранением данных в ЕС)",
            "OpenAI (ევროკავშირში მონაცემების შენახვის პროექტი)",
        ),
        purpose=texts(
            "Language model that writes the assistant's replies, checks them "
            "against the Client's facts, summarises conversations, transcribes "
            "customers' voice notes and grades the assistant's automatic checks "
            "and a small sample of real conversations",
            "Языковая модель, которая пишет ответы помощника, сверяет их с "
            "фактами Клиента, кратко пересказывает разговоры, расшифровывает "
            "голосовые сообщения клиентов и оценивает автоматические проверки "
            "помощника и небольшую выборку настоящих разговоров",
            "ენობრივი მოდელი, რომელიც ასისტენტის პასუხებს წერს, ადარებს მათ "
            "კლიენტის ფაქტებს, მოკლედ აჯამებს საუბრებს, გადაჰყავს ტექსტად "
            "მომხმარებლების ხმოვანი შეტყობინებები და აფასებს ასისტენტის "
            "ავტომატურ შემოწმებებსა და რეალური საუბრების მცირე შერჩევას",
        ),
        personal_data=texts(
            "Messages and voice notes, the Client's knowledge, booking details",
            "Сообщения и голосовые сообщения, знания Клиента, данные броней",
            "შეტყობინებები და ხმოვანი შეტყობინებები, კლიენტის ცოდნა, "
            "ჯავშნების მონაცემები",
        ),
        location=texts(
            "EU (data residency)",
            "ЕС (хранение в ЕС)",
            "ევროკავშირი (შენახვა ევროკავშირში)",
        ),
        client_modules=modules("openai"),
        flows=list(ProcessorFlow),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("elevenlabs"),
        name=texts(
            "ElevenLabs (EU residency)",
            "ElevenLabs (размещение в ЕС)",
            "ElevenLabs (განთავსება ევროკავშირში)",
        ),
        purpose=texts(
            "Voice agent: speech recognition and speech synthesis on calls",
            "Голосовой агент: распознавание и синтез речи в звонках",
            "ხმოვანი აგენტი: მეტყველების ამოცნობა და სინთეზი ზარებში",
        ),
        personal_data=texts(
            "Call audio, transcripts, caller number",
            "Аудио звонков, расшифровки, номер звонящего",
            "ზარების აუდიო, ტრანსკრიპტები, აბონენტის ნომერი",
        ),
        location=texts("EU", "ЕС", "ევროკავშირი"),
        client_modules=modules("elevenlabs"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("langfuse"),
        name=texts("Langfuse", "Langfuse", "Langfuse"),
        purpose=texts(
            "Records of language model calls for quality control",
            "Журнал вызовов языковой модели для контроля качества",
            "ენობრივი მოდელის გამოძახებების ჟურნალი ხარისხის კონტროლისთვის",
        ),
        personal_data=texts(
            "Prompts and replies, which may contain personal data",
            "Запросы и ответы, которые могут содержать персональные данные",
            "მოთხოვნები და პასუხები, რომლებიც შეიძლება პერსონალურ მონაცემებს შეიცავდეს",
        ),
        location=texts("EU region", "Регион ЕС", "ევროკავშირის რეგიონი"),
        client_modules=modules("langfuse"),
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("anthropic"),
        name=texts("Anthropic", "Anthropic", "Anthropic"),
        purpose=texts(
            "Grading the assistant's automatic checks (synthetic conversations "
            "built from the Client's knowledge); and only when the Provider "
            "switches the language model to Anthropic (Claude): writing, "
            "checking and summarising the assistant's replies and grading a "
            "small sample of real conversations",
            "Оценка автоматических проверок помощника (искусственных разговоров, "
            "составленных по знаниям Клиента); и только если Поставщик "
            "переключил языковую модель на Anthropic (Claude): ответы помощника, "
            "их проверка, краткие пересказы и оценка небольшой выборки "
            "настоящих разговоров",
            "ასისტენტის ავტომატური შემოწმებების შეფასება (კლიენტის ცოდნით "
            "შედგენილი ხელოვნური საუბრები); და მხოლოდ მაშინ, თუ მომწოდებელმა "
            "ენობრივი მოდელი Anthropic-ზე (Claude) გადართო: ასისტენტის "
            "პასუხები, მათი შემოწმება, მოკლე შეჯამებები და რეალური საუბრების "
            "მცირე შერჩევის შეფასება",
        ),
        personal_data=texts(
            "The Client's knowledge; messages and booking details only after "
            "the switch",
            "Знания Клиента; сообщения и данные броней — только после переключения",
            "კლიენტის ცოდნა; შეტყობინებები და ჯავშნების მონაცემები — მხოლოდ "
            "გადართვის შემდეგ",
        ),
        location=texts(
            "[United States; transfer mechanism to be confirmed]",
            "[США; механизм передачи уточнить]",
            "[აშშ; გადაცემის მექანიზმი დასაზუსტებელია]",
        ),
        client_modules=modules("anthropic"),
        flows=[ProcessorFlow.AUTOTEST_JUDGE],
        chat_provider_flows=[
            ProcessorFlow.ASSISTANT_REPLIES,
            ProcessorFlow.CLAIM_VERIFIER,
            ProcessorFlow.CONVERSATION_SUMMARIES,
            ProcessorFlow.QUALITY_SAMPLING,
        ],
        added_on=ORIGINAL_LIST_DATE,
    ),
    SubprocessorEntry(
        key=key("anthropic_quality_review"),
        name=texts(
            "Anthropic (quality review of conversations)",
            "Anthropic (проверка качества разговоров)",
            "Anthropic (საუბრების ხარისხის შემოწმება)",
        ),
        purpose=texts(
            "Grading a small nightly sample of real conversations for quality "
            "when the Provider chooses Anthropic as the judge; each Client can "
            "turn the sample off in Settings, Privacy",
            "Оценка качества небольшой ночной выборки настоящих разговоров, "
            "если Поставщик выбрал Anthropic оценщиком; каждый Клиент может "
            "отключить выборку в «Настройки», «Приватность»",
            "რეალური საუბრების მცირე ღამის შერჩევის ხარისხის შეფასება, თუ "
            "მომწოდებელმა შემფასებლად Anthropic აირჩია; თითოეულ კლიენტს "
            "შეუძლია შერჩევის გამორთვა: „პარამეტრები“, „კონფიდენციალურობა“",
        ),
        personal_data=texts(
            "Messages of the sampled conversations with phone numbers and "
            "e-mail addresses removed (names and free text, which may describe "
            "health, stay), the Client's knowledge",
            "Сообщения выбранных разговоров без телефонов и адресов почты (имена "
            "и свободный текст, в том числе о здоровье, остаются), знания "
            "Клиента",
            "შერჩეული საუბრების შეტყობინებები ტელეფონებისა და ელფოსტის "
            "მისამართების გარეშე (სახელები და თავისუფალი ტექსტი, მათ შორის "
            "ჯანმრთელობაზე, რჩება), კლიენტის ცოდნა",
        ),
        location=texts(
            "[United States; transfer mechanism to be confirmed]",
            "[США; механизм передачи уточнить]",
            "[აშშ; გადაცემის მექანიზმი დასაზუსტებელია]",
        ),
        client_modules=modules("anthropic"),
        flows=[ProcessorFlow.QUALITY_SAMPLING],
        added_on=ANTHROPIC_QUALITY_FROM,
        addition_announced_on=ANTHROPIC_QUALITY_ANNOUNCED_ON,
    ),
)
