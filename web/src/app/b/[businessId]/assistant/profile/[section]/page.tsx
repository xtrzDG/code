import { notFound } from "next/navigation";

import { pageMetadata } from "@/components/business/pageMetadata";
import { isProfileSection } from "@/lib/profile/sections";

import { SectionEditor } from "../_components/SectionEditor";

export async function generateMetadata({ params }: PageProps<"/b/[businessId]/assistant/profile/[section]">) {
  const { section } = await params;
  return pageMetadata("assistant/profile", isProfileSection(section) ? `profileEdit.sections.${section}.title` : undefined)();
}

/** One section of the business profile (business, place, offer, hours, people, rules), saved as the owner types. */
export default async function ProfileSectionPage({ params }: PageProps<"/b/[businessId]/assistant/profile/[section]">) {
  const { section } = await params;
  if (!isProfileSection(section)) {
    notFound();
  }
  return <SectionEditor key={section} section={section} />;
}
