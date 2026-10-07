import { redirect } from "next/navigation";

import { profilePath, profileSectionPath, sectionOfStepParam } from "@/lib/profile/sections";
import { setupPath } from "@/lib/navigation";
import { getBusiness } from "@/server/api";

/**
 * The old address of the setup flow. Before the assistant exists it leads
 * into the tunnel (/b/{id}/setup, where the owner left off); afterwards
 * the same questions live in Assistant → Business profile, and an old
 * step (`?step=offer`) opens the section that edits it now.
 */
export default async function OnboardingRedirect({ params, searchParams }: PageProps<"/b/[businessId]/onboarding">) {
  const [{ businessId }, { step }] = await Promise.all([params, searchParams]);
  const business = await getBusiness(businessId);
  if (business.status === "onboarding") {
    redirect(setupPath(business.id));
  }
  const section = sectionOfStepParam(step);
  redirect(section ? profileSectionPath(business.id, section) : profilePath(business.id));
}
