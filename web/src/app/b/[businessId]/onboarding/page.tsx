import { redirect } from "next/navigation";

import { getI18n } from "@/i18n/server";
import { businessPath } from "@/lib/navigation";
import { getBusiness } from "@/server/api";

import { OnboardingWizard } from "../assistant/profile/OnboardingWizard";

export async function generateMetadata() {
  const { t } = await getI18n();
  return { title: t("setup.navEntry") };
}

/** Query parameters as a search string ("?step=offer"), for a redirect that keeps them. */
function searchOf(params: Record<string, string | string[] | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    for (const item of Array.isArray(value) ? value : value === undefined ? [] : [value]) {
      search.append(key, item);
    }
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

/**
 * The setup flow, "Create an AI assistant": the six-step profile shown on
 * its own (the business frame hides the sections around it). Once the
 * assistant exists the same steps live under Assistant → Hours and rules,
 * and old links (`?step=offer`) go there.
 */
export default async function SetupPage({ params, searchParams }: PageProps<"/b/[businessId]/onboarding">) {
  const [{ businessId }, query] = await Promise.all([params, searchParams]);
  const business = await getBusiness(businessId);
  if (business.status !== "onboarding") {
    redirect(`${businessPath(business.id, "assistant/profile")}${searchOf(query)}`);
  }
  return <OnboardingWizard />;
}
