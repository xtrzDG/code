import { redirect } from "next/navigation";

import { businessPath, setupPath } from "@/lib/navigation";
import { getBusiness } from "@/server/api";

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
 * The old address of the setup flow. Before the assistant exists it leads
 * into the tunnel (/b/{id}/setup, where the owner left off); afterwards
 * the same questions live under Assistant → Hours and rules, and old links
 * (`?step=offer`) go there.
 */
export default async function OnboardingRedirect({ params, searchParams }: PageProps<"/b/[businessId]/onboarding">) {
  const [{ businessId }, query] = await Promise.all([params, searchParams]);
  const business = await getBusiness(businessId);
  if (business.status === "onboarding") {
    redirect(setupPath(business.id));
  }
  redirect(`${businessPath(business.id, "assistant/profile")}${searchOf(query)}`);
}
