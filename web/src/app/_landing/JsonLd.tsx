import { serializeJsonLd, type JsonLd as JsonLdData } from "@/lib/publicSite/seo";

/**
 * Structured data for search engines beside the page. A data block, not a
 * script: browsers never run it, and "<" is escaped so no text in it can
 * close the tag.
 */
export function JsonLd({ data }: { data: JsonLdData | readonly JsonLdData[] }) {
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: serializeJsonLd(data) }} />;
}
