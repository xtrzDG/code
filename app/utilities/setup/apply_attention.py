"""
Why applied changes are not live, in words an owner can act on: failed
go-live checks and refusals turned into attention reasons, their texts in
English, Russian and Georgian, and the place where each is fixed.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestOutcome, GoLiveCheckCode
from app.schemas.constants.setup import ApplyAttentionCode, SetupActionTarget
from app.schemas.domain.assistants import AutotestRunDocument
from app.schemas.domain.setup import ApplyAttentionReason
from app.schemas.dto.go_live import GoLiveCheck
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.constrained_strings import GoLiveCheckDetail
from app.utilities.knowledge.localized_texts import build_localized_text

CHECK_ATTENTION: dict[GoLiveCheckCode, ApplyAttentionCode] = {
    GoLiveCheckCode.SUBSCRIPTION_OR_TRIAL: ApplyAttentionCode.PAYMENT_NEEDED,
    GoLiveCheckCode.DPA: ApplyAttentionCode.AGREEMENT_NOT_ACCEPTED,
    GoLiveCheckCode.PROFILE_GAPS: ApplyAttentionCode.PROFILE_INCOMPLETE,
    GoLiveCheckCode.STAFF_CONTACT: ApplyAttentionCode.STAFF_CONTACT_MISSING,
    GoLiveCheckCode.AUTOTESTS: ApplyAttentionCode.CHECKS_FAILED,
    GoLiveCheckCode.VOICE_CONFIGURATION: ApplyAttentionCode.VOICE_NOT_READY,
}

ATTENTION_TARGETS: dict[ApplyAttentionCode, SetupActionTarget] = {
    ApplyAttentionCode.PROFILE_INCOMPLETE: SetupActionTarget.PROFILE,
    ApplyAttentionCode.STAFF_CONTACT_MISSING: SetupActionTarget.STAFF_CONTACTS,
    ApplyAttentionCode.AGREEMENT_NOT_ACCEPTED: SetupActionTarget.AGREEMENT,
    ApplyAttentionCode.PAYMENT_NEEDED: SetupActionTarget.BILLING,
    ApplyAttentionCode.BUILD_FAILED: SetupActionTarget.PROFILE,
    ApplyAttentionCode.CHECKS_FAILED: SetupActionTarget.CHECKS,
    ApplyAttentionCode.CHECKS_STOPPED: SetupActionTarget.APPLY_CHANGES,
    ApplyAttentionCode.VOICE_NOT_READY: SetupActionTarget.APPLY_CHANGES,
    ApplyAttentionCode.PUBLISH_FAILED: SetupActionTarget.APPLY_CHANGES,
}

ATTENTION_TEXTS: dict[ApplyAttentionCode, LocalizedText] = {
    ApplyAttentionCode.PROFILE_INCOMPLETE: build_localized_text(
        en="Some required details are missing in your profile.",
        ru="В анкете не хватает обязательных данных.",
        ka="ანკეტაში აკლია სავალდებულო მონაცემები.",
    ),
    ApplyAttentionCode.STAFF_CONTACT_MISSING: build_localized_text(
        en="Add someone who receives bookings and requests from the assistant.",
        ru="Добавьте сотрудника, который будет получать брони и заявки от помощника.",
        ka="დაამატეთ თანამშრომელი, რომელიც მიიღებს ჯავშნებსა და მოთხოვნებს "
        "ასისტენტისგან.",
    ),
    ApplyAttentionCode.AGREEMENT_NOT_ACCEPTED: build_localized_text(
        en="Accept the data processing agreement to go live.",
        ru="Чтобы запустить помощника, примите соглашение об обработке данных.",
        ka="ასისტენტის გასაშვებად მიიღეთ მონაცემთა დამუშავების შეთანხმება.",
    ),
    ApplyAttentionCode.PAYMENT_NEEDED: build_localized_text(
        en="Your plan needs a payment before the assistant can go live.",
        ru="Чтобы запустить помощника, оплатите тариф.",
        ka="ასისტენტის გასაშვებად გადაიხადეთ ტარიფი.",
    ),
    ApplyAttentionCode.BUILD_FAILED: build_localized_text(
        en="The assistant could not be built from your profile. Check the "
        "profile and try again.",
        ru="Не удалось собрать помощника по анкете. Проверьте анкету и попробуйте "
        "снова.",
        ka="ანკეტიდან ასისტენტის აწყობა ვერ მოხერხდა. შეამოწმეთ ანკეტა და სცადეთ "
        "ხელახლა.",
    ),
    ApplyAttentionCode.CHECKS_FAILED: build_localized_text(
        en="The automatic checks found answers to improve. See what went wrong, "
        "fix the profile and apply the changes again.",
        ru="Автоматическая проверка нашла ответы, которые нужно улучшить. "
        "Посмотрите, что пошло не так, поправьте анкету и примените изменения "
        "снова.",
        ka="ავტომატურმა შემოწმებამ იპოვა პასუხები, რომლებიც გასაუმჯობესებელია. "
        "ნახეთ, რა იყო არასწორი, შეასწორეთ ანკეტა და ცვლილებები ხელახლა "
        "გამოიყენეთ.",
    ),
    ApplyAttentionCode.CHECKS_STOPPED: build_localized_text(
        en="The automatic checks stopped before the end. Please apply the "
        "changes again.",
        ru="Автоматическая проверка прервалась. Примените изменения ещё раз.",
        ka="ავტომატური შემოწმება შეწყდა. გთხოვთ, ცვლილებები ხელახლა გამოიყენოთ.",
    ),
    ApplyAttentionCode.VOICE_NOT_READY: build_localized_text(
        en="Phone answering could not be set up right now. Try again in a few minutes.",
        ru="Не удалось настроить ответы на звонки. Попробуйте ещё раз через "
        "несколько минут.",
        ka="სატელეფონო პასუხების დაყენება ვერ მოხერხდა. სცადეთ ხელახლა რამდენიმე "
        "წუთში.",
    ),
    ApplyAttentionCode.PUBLISH_FAILED: build_localized_text(
        en="The new version could not be turned on. Please try again.",
        ru="Не удалось включить новую версию. Попробуйте ещё раз.",
        ka="ახალი ვერსიის ჩართვა ვერ მოხერხდა. გთხოვთ, სცადოთ ხელახლა.",
    ),
}


def attention_from_checks(
    checks: Sequence[GoLiveCheck],
    ignored: frozenset[GoLiveCheckCode] = frozenset(),
) -> list[ApplyAttentionReason]:
    """The failed blocking checks (except `ignored`) as attention reasons."""

    return [
        ApplyAttentionReason(
            code=CHECK_ATTENTION[check.code], details=list(check.details)
        )
        for check in checks
        if check.is_blocking and not check.is_ok and check.code not in ignored
    ]


def attention_from_refusal(error: ApplicationError) -> list[ApplyAttentionReason]:
    """
    A refused publish as attention reasons: each failed go-live check by its
    code; anything else (a version state, a missing reason) as a failed
    publish.
    """

    check_codes: dict[str, GoLiveCheckCode] = {
        code.value: code for code in CHECK_ATTENTION
    }
    reasons: list[ApplyAttentionReason] = []
    for reason in error.reasons:
        check_code: GoLiveCheckCode | None = check_codes.get(str(reason.code))
        reasons.append(
            ApplyAttentionReason(code=ApplyAttentionCode.PUBLISH_FAILED)
            if check_code is None
            else ApplyAttentionReason(
                code=CHECK_ATTENTION[check_code],
                details=[GoLiveCheckDetail(str(detail)) for detail in reason.details],
            )
        )

    return reasons or [ApplyAttentionReason(code=ApplyAttentionCode.PUBLISH_FAILED)]


def failed_scenario_kinds(run: AutotestRunDocument | None) -> list[GoLiveCheckDetail]:
    """The kinds of the checks that did not pass (prices, bookings...), once each."""

    if run is None:
        return []

    return [
        GoLiveCheckDetail(kind)
        for kind in dict.fromkeys(
            result.kind.value
            for result in run.results
            if result.outcome is not AutotestOutcome.PASSED
        )
    ]
