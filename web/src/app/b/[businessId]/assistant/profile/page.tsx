import { redirect } from "next/navigation";

import { pageMetadata } from "@/components/business/pageMetadata";
import { profileSectionPath, sectionOfStepParam } from "@/lib/profile/sections";

import { ProfileOverview } from "./ProfileOverview";

export const generateMetadata = pageMetadata("assistant/profile");

/**
 * Assistant → Business profile: the cards of its six sections. Addresses
 * of the old six-step profile (`?step=booking_rules`) open the section
 * that edits that step now.
 */
export default async function ProfilePage({ params, searchParams }: PageProps<"/b/[businessId]/assistant/profile">) {
  const [{ businessId }, { step }] = await Promise.all([params, searchParams]);
  const section = sectionOfStepParam(step);
  if (section) {
    redirect(profileSectionPath(businessId, section));
  }
  return <ProfileOverview />;
}
