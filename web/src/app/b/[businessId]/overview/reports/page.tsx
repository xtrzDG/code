import { pageMetadata } from "@/components/business/pageMetadata";
import { isReportKind } from "@/components/value/valueModel";

import { ReportsScreen } from "./ReportsScreen";

export const generateMetadata = pageMetadata("overview/reports");

/** Overview → Reports; `?kind=weekly` lists the weekly digests, `?report=` opens one (a digest's link). */
export default async function ReportsPage({ searchParams }: PageProps<"/b/[businessId]/overview/reports">) {
  const { kind, report } = await searchParams;
  return (
    <ReportsScreen
      initialKind={isReportKind(kind) ? kind : null}
      openedReportId={typeof report === "string" && /^value_report_[0-9a-f-]{36}$/.test(report) ? report : null}
    />
  );
}
