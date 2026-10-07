import type { NicheSummaryView } from "@/api/types";
import { IconCalendar, IconChat, IconHandoff, IconPlug, IconShield } from "@/components/icons";
import { Stagger, StaggerItem } from "@/components/siteMotion";
import type { Translator } from "@/i18n/translate";
import { listFormat } from "@/lib/intl/formatters";
import { liveIntegrations } from "@/lib/publicSite/paths";
import type { PlanQuote } from "@/lib/publicSite/prices";

import { IconTile, Section } from "../Section";

/**
 * What the assistant does for this kind of business (booking only where
 * it books), the integrations it works with today and the plans such
 * businesses usually start with.
 */
export function NicheAbilities({
  t,
  locale,
  niche,
  quotes,
}: {
  t: Translator["t"];
  locale: string;
  niche: NicheSummaryView;
  quotes: readonly PlanQuote[] | null;
}) {
  const abilities = [
    {
      icon: <IconCalendar className="size-4" />,
      text: niche.takes_bookings ? t("nichePage.books", { resource: niche.resource_noun }) : t("nichePage.noBookings"),
    },
    { icon: <IconChat className="size-4" />, text: t("nichePage.answers") },
    { icon: <IconHandoff className="size-4" />, text: t("nichePage.handoff") },
    ...(niche.requires_legal_review ? [{ icon: <IconShield className="size-4" />, text: t("nichePage.sensitive") }] : []),
  ];
  const integrations = liveIntegrations(niche.integrations);
  const planNames = niche.recommended_plans
    .map((key) => quotes?.find((quote) => quote.plan_key === key)?.name)
    .filter((name): name is string => Boolean(name));
  const list = listFormat(locale, { type: "disjunction" });

  return (
    <Section id="does" title={t("nichePage.doesTitle")}>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Stagger as="ul" step={0.08} className="space-y-3">
          {abilities.map((ability) => (
            <StaggerItem as="li" key={ability.text} className="flex items-start gap-3 rounded-xl border border-line bg-surface p-4">
              <IconTile>{ability.icon}</IconTile>
              <span className="pt-1.5 text-sm text-pretty text-ink">{ability.text}</span>
            </StaggerItem>
          ))}
        </Stagger>
        <div className="space-y-4">
          {planNames.length > 0 ? (
            <div className="rounded-xl border border-line bg-surface p-5">
              <h3 className="text-sm font-semibold text-ink">{t("nichePage.plansTitle")}</h3>
              <p className="mt-2 text-sm text-pretty text-ink-muted">{t("nichePage.plansText", { plans: list.format(planNames) })}</p>
              <a href="#pricing" className="mt-3 inline-block text-sm font-medium text-accent underline-offset-4 hover:underline">
                {t("nichePage.pricingLink")}
              </a>
            </div>
          ) : null}
          {integrations.length > 0 ? (
            <div className="flex items-start gap-3 rounded-xl border border-line bg-surface p-5">
              <IconTile>
                <IconPlug className="size-4" />
              </IconTile>
              <div>
                <h3 className="text-sm font-semibold text-ink">{t("nichePage.integrationsTitle")}</h3>
                <p className="mt-1 text-sm text-ink-muted">{listFormat(locale, { type: "conjunction" }).format(integrations)}</p>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </Section>
  );
}
