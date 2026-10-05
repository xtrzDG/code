import { IconCheck } from "@/components/icons";
import type { Translator } from "@/i18n/translate";
import { moneyLabel, type PlanQuote } from "@/lib/publicSite/prices";

import { Section } from "./Section";

const SELF_POINTS = ["guide", "test", "channels"] as const;
const DONE_POINTS = ["knowledge", "channels", "launch"] as const;

/** The done-for-you fee in the currency the plan is billed in (never a conversion). */
function doneForYouFee(quote: PlanQuote, locale: string): string | null {
  const option = (quote.setup_options ?? []).find((candidate) => candidate.option === "done_for_you");
  if (!option) {
    return null;
  }
  const fee = option.local_fee && !option.local_fee.is_estimated ? option.local_fee : option.fee;
  return moneyLabel(fee.money, locale);
}

/** Self-serve against done-for-you setup, side by side, with the one-time fee of the latter. */
export function SetupOptions({ translator, quote }: { translator: Translator; quote: PlanQuote | null }) {
  const { t, locale } = translator;
  const fee = quote ? doneForYouFee(quote, locale) : null;
  if (fee === null) {
    return null;
  }
  const column = (title: string, price: string, points: readonly string[], prefix: string, featured: boolean) => (
    <div className={featured ? "rounded-2xl border border-accent/30 bg-surface p-6" : "rounded-2xl border border-line bg-surface p-6"}>
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-ink tabular-nums">{price}</p>
      <ul className="mt-5 space-y-2.5 text-sm text-ink">
        {points.map((point) => (
          <li key={point} className="flex gap-2.5">
            <IconCheck className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden />
            <span>{t(`publicPricing.setup.${prefix}.${point}` as Parameters<typeof t>[0])}</span>
          </li>
        ))}
      </ul>
    </div>
  );
  return (
    <Section id="setup" title={t("publicPricing.setup.title")} subtitle={t("publicPricing.setup.subtitle")}>
      <div className="grid gap-4 md:grid-cols-2" data-testid="setup-options">
        {column(t("publicPricing.setup.selfTitle"), t("publicPricing.setup.selfPrice"), SELF_POINTS, "selfPoints", true)}
        {column(t("publicPricing.setup.doneTitle"), t("publicPricing.setup.donePrice", { price: fee }), DONE_POINTS, "donePoints", false)}
      </div>
      <p className="mt-4 text-xs text-ink-subtle">{t("publicPricing.setup.note")}</p>
    </Section>
  );
}
