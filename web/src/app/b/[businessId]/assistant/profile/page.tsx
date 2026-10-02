import { pageMetadata } from "@/components/business/pageMetadata";

import { OnboardingWizard } from "./OnboardingWizard";

export const generateMetadata = pageMetadata("assistant/profile");

/** Hours and rules: the six-step business profile; `?step=offer` opens a step directly. */
export default function ProfilePage() {
  return <OnboardingWizard />;
}
