import { SectionLoading } from "@/components/business/SectionLoading";
import { SkeletonCard } from "@/components/ui";

export default function ReturnVisitsLoading() {
  return (
    <SectionLoading page="bookings/return-visits" label="returnVisits.loading">
      <div className="space-y-6">
        <SkeletonCard lines={6} />
        <SkeletonCard lines={3} />
      </div>
    </SectionLoading>
  );
}
