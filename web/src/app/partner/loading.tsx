import { PartnerSkeleton } from "./_components/PartnerScreen";

/** The partner portal while it loads. */
export default function PartnerLoading() {
  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
      <PartnerSkeleton />
    </main>
  );
}
