import { BrandFrame } from "../_components/BrandFrame";

/** One brand: its header and tabs around the overview, the team and the shared answers. */
export default async function BrandLayout({ children, params }: LayoutProps<"/brands/[brandId]">) {
  const { brandId } = await params;
  return (
    <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
      <BrandFrame brandId={brandId}>{children}</BrandFrame>
    </main>
  );
}
