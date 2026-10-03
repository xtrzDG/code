"use client";

import type { Schema } from "@/api/types";
import { Badge, Card } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import type { AdminClientSummary } from "../../_lib/clients";
import { useClientFormat } from "../../_lib/useClientFormat";
import { BUSINESS_STATUS_LABELS, PLAN_LABELS, SUBSCRIPTION_LABELS } from "../labels";

/** The active version's stored verdict: passed or not, and how many scenarios passed when the run counted them. */
function VerdictValue({ verdict }: { verdict: Schema<"ClientAutotestVerdict"> }) {
  const { t, locale } = useI18n();
  const counted = verdict.passed_count !== null && verdict.passed_count !== undefined && Boolean(verdict.scenario_count);
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <Badge tone={verdict.is_passed ? "success" : "danger"}>
        {t(verdict.is_passed ? "admin.detail.facts.verdictPassed" : "admin.detail.facts.verdictFailed", {
          number: verdict.version_number,
        })}
      </Badge>
      {counted ? (
        <span className="text-sm text-ink-muted">
          {t("admin.detail.facts.verdictCounts", {
            passed: formatNumber(verdict.passed_count ?? 0, locale),
            total: formatNumber(verdict.scenario_count ?? 0, locale),
          })}
        </span>
      ) : null}
    </span>
  );
}

/** Who sets the client up (the subscription's setup option) and the team's onboarding request. */
function SetupValue({ summary, date }: { summary: AdminClientSummary; date: (microseconds: number) => string }) {
  const { t } = useI18n();
  const request = summary.onboarding_request;
  const option =
    summary.setup_option === "done_for_you"
      ? t("admin.detail.facts.setupDoneForYou")
      : summary.setup_option === "self_serve"
        ? t("admin.detail.facts.setupSelfServe")
        : t("admin.detail.facts.setupNotChosen");
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <span>{option}</span>
      {request ? (
        <Badge tone={request.status === "open" ? "warning" : "success"}>
          {request.status === "open"
            ? t("admin.detail.facts.onboardingOpen", { date: date(request.requested_at) })
            : t("admin.detail.facts.onboardingDone")}
        </Badge>
      ) : null}
    </span>
  );
}

/** The client's status, plan, subscription, setup, published version and recent trouble. */
export function OverviewCard({ summary, timeZone }: { summary: AdminClientSummary; timeZone: string }) {
  const { t, locale } = useI18n();
  const { date, dateTime } = useClientFormat(timeZone);
  return (
    <Card title={t("admin.detail.overviewTitle")} className="xl:col-span-2">
      <Facts
        columns={3}
        items={[
          { label: t("admin.detail.facts.status"), value: t(BUSINESS_STATUS_LABELS[summary.business_status]) },
          {
            label: t("admin.detail.facts.serviceMode"),
            value: (
              <Badge tone={summary.service_mode === "full" ? "success" : "danger"}>
                {t(summary.service_mode === "full" ? "billing.serviceModes.full" : "billing.serviceModes.leads_only")}
              </Badge>
            ),
          },
          {
            label: t("admin.detail.facts.plan"),
            value: [
              t(PLAN_LABELS[summary.plan_key]),
              summary.billing_period
                ? t(summary.billing_period === "annual" ? "billing.periodNames.annual" : "billing.periodNames.monthly")
                : null,
            ]
              .filter(Boolean)
              .join(" · "),
          },
          {
            label: t("admin.detail.facts.subscription"),
            value: summary.subscription_status ? t(SUBSCRIPTION_LABELS[summary.subscription_status]) : t("admin.noSubscription"),
          },
          summary.period_end ? { label: t("admin.detail.facts.periodEnd"), value: date(summary.period_end) } : null,
          summary.grace_until ? { label: t("admin.detail.facts.graceUntil"), value: date(summary.grace_until) } : null,
          {
            label: t("admin.detail.facts.autoDebit"),
            value: summary.has_auto_debit ? t("billing.facts.autoDebitOn") : t("common.no"),
          },
          { label: t("admin.detail.facts.setup"), value: <SetupValue summary={summary} date={date} /> },
          {
            label: t("admin.detail.facts.published"),
            value:
              summary.published_version_number !== null && summary.published_version_number !== undefined
                ? t("admin.detail.facts.publishedValue", {
                    number: summary.published_version_number,
                    date: summary.published_at ? dateTime(summary.published_at) : "",
                  })
                : t("admin.detail.facts.notPublished"),
          },
          {
            label: t("admin.detail.facts.testScore"),
            value:
              summary.last_test_score !== null && summary.last_test_score !== undefined
                ? `${formatNumber(summary.last_test_score, locale, { maximumFractionDigits: 1 })} / 5`
                : t("admin.unknown"),
          },
          {
            label: t("admin.detail.facts.verdict"),
            value: summary.autotest_verdict ? <VerdictValue verdict={summary.autotest_verdict} /> : t("admin.unknown"),
          },
          { label: t("admin.detail.facts.failedTests"), value: formatNumber(summary.failed_tests, locale) },
          { label: t("admin.detail.facts.handoffs"), value: formatNumber(summary.handoffs_last_7_days, locale) },
          { label: t("admin.detail.facts.toolErrors"), value: formatNumber(summary.tool_errors_last_7_days, locale) },
          { label: t("admin.detail.facts.openQuestions"), value: formatNumber(summary.open_unanswered_questions, locale) },
          { label: t("admin.detail.facts.timezone"), value: timeZone },
        ]}
      />
    </Card>
  );
}
