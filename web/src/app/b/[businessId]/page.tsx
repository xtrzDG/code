import { redirect } from "next/navigation";

import { businessPath } from "@/lib/navigation";
import { getBusiness } from "@/server/api";

/**
 * /b/{id} opens the overview; before the assistant exists the overview is
 * the "Create an AI assistant" page (the business frame shows it instead of
 * every section).
 */
export default async function BusinessIndexPage({ params }: PageProps<"/b/[businessId]">) {
  const { businessId } = await params;
  const business = await getBusiness(businessId);
  redirect(businessPath(business.id));
}
