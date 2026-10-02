import { SectionLoading } from "@/components/business/SectionLoading";

import { DashboardSkeleton } from "./_components/DashboardSkeleton";

export default function DashboardLoading() {
  return (
    <SectionLoading section="dashboard" label="dashboard.loading">
      <DashboardSkeleton />
    </SectionLoading>
  );
}
