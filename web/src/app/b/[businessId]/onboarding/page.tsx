import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { OnboardingWizard } from "./OnboardingWizard";

export const generateMetadata = sectionMetadata("onboarding");

/** The six-step business profile; `?step=offer` opens a step directly. */
export default async function OnboardingPage({ searchParams }: PageProps<"/b/[businessId]/onboarding">) {
  const { step } = await searchParams;
  return <OnboardingWizard initialStep={typeof step === "string" ? step : null} />;
}
