import type { Metadata } from "next";

import { BusinessProvider } from "@/components/business/BusinessContext";
import { BusinessShell } from "@/components/shell/BusinessShell";
import { getBusiness, getCurrentUser } from "@/server/api";

export async function generateMetadata({ params }: LayoutProps<"/b/[businessId]">): Promise<Metadata> {
  const { businessId } = await params;
  const business = await getBusiness(businessId);
  return { title: { default: business.name, template: `%s · ${business.name}` } };
}

/**
 * Every /b/[businessId]/* page: loads the business and the user once (404
 * for a business the user may not open) and renders the sidebar.
 */
export default async function BusinessLayout({ children, params }: LayoutProps<"/b/[businessId]">) {
  const { businessId } = await params;
  const [me, business] = await Promise.all([getCurrentUser(), getBusiness(businessId)]);

  return (
    <BusinessProvider business={business} me={me}>
      <BusinessShell>{children}</BusinessShell>
    </BusinessProvider>
  );
}
