import { SectionLoading } from "@/components/business/SectionLoading";
import { SkeletonCard } from "@/components/ui";

export default function CustomerLoading() {
  return (
    <SectionLoading page="customers" label="customers.loading">
      <div className="space-y-6">
        <SkeletonCard header={false} lines={2} />
        <div className="grid gap-6 lg:grid-cols-3">
          <SkeletonCard lines={6} className="lg:col-span-2" />
          <SkeletonCard lines={3} />
        </div>
      </div>
    </SectionLoading>
  );
}
