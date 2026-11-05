import type { NicheSummaryView } from "@/api/types";
import type { Translator } from "@/i18n/translate";
import type { PlanQuote } from "@/lib/publicSite/prices";
import { roiNiches, roiPlans } from "@/lib/publicSite/roiOptions";

import { RoiCalculator } from "./roi/RoiCalculator";
import { Section } from "./Section";

/** The value calculator's block; nothing without plans to compare with. */
export function Roi({
  t,
  niches,
  quotes,
  initialNicheKey,
  recommendedPlans,
}: {
  t: Translator["t"];
  niches: readonly NicheSummaryView[] | null;
  quotes: readonly PlanQuote[] | null;
  initialNicheKey?: string;
  recommendedPlans?: readonly string[];
}) {
  if (!quotes || quotes.length === 0) {
    return null;
  }
  return (
    <Section id="roi" title={t("roi.title")} subtitle={t("roi.subtitle")} glow="left">
      <RoiCalculator
        niches={roiNiches(niches ?? [])}
        plans={roiPlans(quotes)}
        initialNicheKey={initialNicheKey}
        recommendedPlans={recommendedPlans}
      />
    </Section>
  );
}
