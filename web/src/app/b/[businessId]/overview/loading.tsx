import { SectionLoading } from "@/components/business/SectionLoading";

import { DashboardSkeleton } from "./_components/DashboardSkeleton";

export default function DashboardLoading() {
  return (
    <SectionLoading page="overview" label="dashboard.loading">
      <DashboardSkeleton />
    </SectionLoading>
  );
}
