import { SectionLoading } from "@/components/business/SectionLoading";
import { SkeletonCard, SkeletonCardList } from "@/components/ui";

export default function ReportsLoading() {
  return (
    <SectionLoading page="overview/reports" label="reports.loading">
      <div className="space-y-6">
        <SkeletonCard lines={4} />
        <SkeletonCardList cards={3} />
      </div>
    </SectionLoading>
  );
}
