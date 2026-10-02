import { SectionLoading } from "@/components/business/SectionLoading";
import { Skeleton, SkeletonCard } from "@/components/ui";

export default function SettingsLoading() {
  return (
    <SectionLoading section="settings" label="common.loading">
      <div className="space-y-6">
        <div className="flex gap-2 overflow-hidden">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} className="h-9 w-28 shrink-0 rounded-lg" />
          ))}
        </div>
        <SkeletonCard lines={3} />
        <SkeletonCard lines={5} />
      </div>
    </SectionLoading>
  );
}
