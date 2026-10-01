import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { isDashboardPeriod } from "./_components/dashboardModel";
import { DashboardScreen } from "./DashboardScreen";

export const generateMetadata = sectionMetadata("dashboard");

/** The dashboard; `?period=7d` opens another period (today, 7d, 30d, 90d). */
export default async function DashboardPage({ searchParams }: PageProps<"/b/[businessId]/dashboard">) {
  const { period } = await searchParams;
  return <DashboardScreen initialPeriod={isDashboardPeriod(period) ? period : null} />;
}
