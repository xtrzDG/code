from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.value import AverageCheckSource, ValueBasis, ValueReportKind
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.dto.value.value_digests import ValueDigestText, ValueDigestTextInput
from app.schemas.dto.value.value_model import ValueTotals
from app.schemas.dto.value.value_reports import ValueReportView
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.transformers.notifications.message_rendering import render
from app.transformers.notifications.value_digest_texts import (
    AFTER_HOURS,
    CHANGE_AGAINST,
    EARNINGS,
    HOURS,
    LINK_LINE,
    MINUTES,
    MONEY,
    NO_CHECK_HINT,
    OPT_OUT,
    OTHER_COUNTS,
    RETURN_ON_PLAN,
    RETURN_SHORT,
    TIME_SAVED,
    TITLES,
    TYPICAL_CHECK_HINT,
)
from app.utilities.scheduling.localized_formatting import choose_template_language
from app.utilities.scheduling.zoned_time import parse_local_date
from app.utilities.value.digest_formatting import (
    format_change,
    format_count,
    format_multiple,
    format_report_period,
    format_whole_money,
    split_minutes,
)


class ValueDigestTextTransformer(
    TransformerContract[ValueDigestTextInput, ValueDigestText]
):
    """
    A stored digest or monthly report in one owner's language: the title
    (the e-mail subject), the period, what the assistant earned (bookings
    or requests, in money when an average check is known, with the change
    against the period before, and how many times it covered the plan's
    price), the conversations after hours, the staff time saved, the other
    counts, a hint about the average check, the link to the report and how
    to turn the summaries off. The device
    notification carries the title and the earnings with the time saved.
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: ValueDigestTextInput) -> ValueDigestText:
        report: ValueReportView = input_data.report
        language: LanguageTag = choose_template_language(
            TITLES[report.kind], input_data.language
        )
        business: str = str(input_data.business_name)
        period: str = format_report_period(
            report.kind,
            parse_local_date(report.date_from),
            parse_local_date(report.date_to),
            language,
        )
        title: str = self._render(
            TITLES[report.kind], language, {"business": business, "month": period}
        )
        earnings: str = self._earnings(report, language)
        time_saved: str = self._time_saved(report.current, language)
        # A month is already in the title; a day or a week gets its own line.
        lines: list[str] = [title]
        if report.kind is not ValueReportKind.MONTHLY:
            lines.append(period)

        lines.append(earnings + self._change(report, language))
        returned: str | None = self._return_on_plan(report, language, RETURN_ON_PLAN)
        if returned is not None:
            lines.append(returned)

        current: ValueTotals = report.current
        lines.append(
            self._render(
                AFTER_HOURS,
                language,
                {
                    "count": format_count(
                        int(current.after_hours_conversation_count), language
                    ),
                    "total": format_count(int(current.conversation_count), language),
                },
            )
        )
        lines.append(time_saved)
        lines.append(
            self._render(
                OTHER_COUNTS[report.value_basis],
                language,
                {
                    "conversations": format_count(
                        int(current.conversation_count), language
                    ),
                    "requests": format_count(int(current.request_count), language),
                    "handoffs": format_count(int(current.handoff_count), language),
                },
            )
        )
        hint: str | None = self._check_hint(report, language)
        if hint is not None:
            lines.append(hint)

        if input_data.link is not None:
            # The address stays as it is, so every mail app recognises it.
            text: str = str(self._text_resolver.resolve(LINK_LINE, language))
            lines.append(text.format(link=str(input_data.link)))

        lines.append(self._render(OPT_OUT, language, {"business": business}))
        summary: list[str] = [period, earnings]
        short_return: str | None = self._return_on_plan(report, language, RETURN_SHORT)
        if short_return is not None:
            summary.append(short_return)

        summary.append(time_saved)
        return ValueDigestText(
            message=MessageText("\n".join(lines)),
            brief=StaffAlertBrief(
                title=StaffAlertTitle(title),
                detail=StaffAlertDetail(f"{earnings} · {time_saved}"),
            ),
            summary=MessageText(" · ".join(summary)),
        )

    def _earnings(self, report: ValueReportView, language: LanguageTag) -> str:
        units: int = earning_units(report.current, report.value_basis)
        line: str = self._render(
            EARNINGS[report.value_basis],
            language,
            {"count": format_count(units, language)},
        )
        money = report.current.estimated_revenue_minor
        if money is not None:
            amount: str = format_whole_money(int(money), report.currency_code, language)
            line = f"{line} {self._render(MONEY, language, {'money': amount})}"

        return line

    def _return_on_plan(
        self,
        report: ValueReportView,
        language: LanguageTag,
        template: LocalizedText,
    ) -> str | None:
        """ "≈ 3.7× the price of your plan" when the money covered it at all."""

        if (
            report.return_multiple is None
            or report.plan_cost_minor is None
            or float(report.return_multiple) <= 0
        ):
            return None

        price: str = format_whole_money(
            int(report.plan_cost_minor), report.currency_code, language
        )
        multiple: str = format_multiple(float(report.return_multiple), language)
        return self._render(template, language, {"multiple": multiple, "price": price})

    def _change(self, report: ValueReportView, language: LanguageTag) -> str:
        """The change against the period before; empty without a comparison."""

        change: str | None = format_change(
            earning_units(report.current, report.value_basis),
            earning_units(report.previous, report.value_basis),
            language,
        )
        if change is None:
            return ""

        against: str = self._render(
            CHANGE_AGAINST[report.kind], language, {"change": change}
        )
        return f" {against}"

    def _time_saved(self, totals: ValueTotals, language: LanguageTag) -> str:
        amount, is_hours = split_minutes(int(totals.staff_minutes_saved))
        time: str = self._render(
            HOURS if is_hours else MINUTES,
            language,
            {"count": format_count(amount, language)},
        )
        return self._render(TIME_SAVED, language, {"time": time})

    def _check_hint(self, report: ValueReportView, language: LanguageTag) -> str | None:
        if report.average_check_source is AverageCheckSource.NONE:
            return self._render(NO_CHECK_HINT, language, {})

        if (
            report.average_check_source is AverageCheckSource.NICHE_DEFAULT
            and report.average_check_minor is not None
        ):
            check: str = format_whole_money(
                int(report.average_check_minor), report.currency_code, language
            )
            return self._render(TYPICAL_CHECK_HINT, language, {"check": check})

        return None

    def _render(
        self,
        template: LocalizedText,
        language: LanguageTag,
        fields: dict[str, str],
    ) -> str:
        return render(self._text_resolver, template, language, fields)


def earning_units(totals: ValueTotals, basis: ValueBasis) -> int:
    """What earns money: the assistant's bookings, or its requests."""

    if basis is ValueBasis.BOOKINGS:
        return int(totals.assistant_booking_count)

    return int(totals.request_count)
