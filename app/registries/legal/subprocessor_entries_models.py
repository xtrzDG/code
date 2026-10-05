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
from app.schemas.dto.legal import SubprocessorEntry

MODEL_SUBPROCESSORS: tuple[SubprocessorEntry, ...] = (
    SubprocessorEntry(
        key=key("openai"),
        name=texts(
            "OpenAI (EU data residency project)",
            "OpenAI (проект с хранением данных в ЕС)",
            "OpenAI (ევროკავშირში მონაცემების შენახვის პროექტი)",
        ),
        purpose=texts(
            "Language model that writes the assistant's replies",
            "Языковая модель, которая пишет ответы помощника",
            "ენობრივი მოდელი, რომელიც ასისტენტის პასუხებს წერს",
        ),
        personal_data=texts(
            "Messages, the Client's knowledge, booking details",
            "Сообщения, знания Клиента, данные броней",
            "შეტყობინებები, კლიენტის ცოდნა, ჯავშნების მონაცემები",
        ),
        location=texts(
            "EU (data residency)",
            "ЕС (хранение в ЕС)",
            "ევროკავშირი (შენახვა ევროკავშირში)",
        ),
        client_modules=modules("openai"),
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
            "Only when the Provider switches the language model to Anthropic "
            "(Claude): writing the assistant's replies and judging its automatic "
            "checks",
            "Только если Поставщик переключил языковую модель на Anthropic "
            "(Claude): ответы помощника и оценка его автоматических проверок",
            "მხოლოდ მაშინ, თუ მომწოდებელმა ენობრივი მოდელი Anthropic-ზე (Claude) "
            "გადართო: ასისტენტის პასუხები და მისი ავტომატური შემოწმებების შეფასება",
        ),
        personal_data=texts(
            "Messages, the Client's knowledge, booking details",
            "Сообщения, знания Клиента, данные броней",
            "შეტყობინებები, კლიენტის ცოდნა, ჯავშნების მონაცემები",
        ),
        location=texts(
            "[United States; transfer mechanism to be confirmed]",
            "[США; механизм передачи уточнить]",
            "[აშშ; გადაცემის მექანიზმი დასაზუსტებელია]",
        ),
        client_modules=modules("anthropic"),
        added_on=ORIGINAL_LIST_DATE,
    ),
)
