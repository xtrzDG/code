import { SectionLoading } from "@/components/business/SectionLoading";
import { Skeleton, SkeletonRows } from "@/components/ui";

export default function CustomersLoading() {
  return (
    <SectionLoading page="customers" label="customers.loading">
      <div className="space-y-5">
        <div className="flex flex-wrap gap-3">
          <Skeleton className="h-9 w-full max-w-md rounded-xl" />
          <Skeleton className="h-9 w-56 rounded-xl" />
        </div>
        <SkeletonRows rows={6} avatar />
      </div>
    </SectionLoading>
  );
}
