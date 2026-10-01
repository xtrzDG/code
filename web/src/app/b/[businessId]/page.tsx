import { redirect } from "next/navigation";

import { businessPath } from "@/lib/navigation";
import { getBusiness } from "@/server/api";

/** /b/{id} opens the profile while it is being filled in, else the dashboard. */
export default async function BusinessIndexPage({ params }: PageProps<"/b/[businessId]">) {
  const { businessId } = await params;
  const business = await getBusiness(businessId);
  redirect(businessPath(business.id, business.status === "onboarding" ? "onboarding" : "dashboard"));
}
