import { BrandsSkeleton } from "./_components/BrandsScreen";

/** /brands while it loads. */
export default function BrandsLoading() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
      <BrandsSkeleton />
    </main>
  );
}
