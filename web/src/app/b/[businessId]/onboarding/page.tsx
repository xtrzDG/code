import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { OnboardingWizard } from "./OnboardingWizard";

export const generateMetadata = sectionMetadata("onboarding");

/** The six-step business profile; `?step=offer` opens a step directly. */
export default function OnboardingPage() {
  return <OnboardingWizard />;
}
