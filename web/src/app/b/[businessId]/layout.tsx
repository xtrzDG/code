import type { Metadata } from "next";
import { cookies } from "next/headers";

import { BusinessProvider } from "@/components/business/BusinessContext";
import { SIDEBAR_COOKIE, readSidebarState } from "@/lib/shellPreferences";
import { getBusiness, getCurrentUser } from "@/server/api";

import { BusinessFrame } from "./_components/BusinessFrame";

export async function generateMetadata({ params }: LayoutProps<"/b/[businessId]">): Promise<Metadata> {
  const { businessId } = await params;
  const business = await getBusiness(businessId);
  return { title: { default: business.name, template: `%s · ${business.name}` } };
}

/**
 * Every /b/[businessId]/* page: loads the business and the user once (404
 * for a business the user may not open) and renders the frame: the five
 * sections, or "Create an AI assistant" before the assistant exists.
 */
export default async function BusinessLayout({ children, params }: LayoutProps<"/b/[businessId]">) {
  const { businessId } = await params;
  const [me, business, cookieStore] = await Promise.all([getCurrentUser(), getBusiness(businessId), cookies()]);
  const collapsed = readSidebarState(cookieStore.get(SIDEBAR_COOKIE)?.value) === "collapsed";

  return (
    <BusinessProvider business={business} me={me}>
      <BusinessFrame initialCollapsed={collapsed}>{children}</BusinessFrame>
    </BusinessProvider>
  );
}
