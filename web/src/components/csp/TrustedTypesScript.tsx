"use client";

import { useServerInsertedHTML } from "next/navigation";
import { useRef } from "react";

import { trustedTypesBootstrap } from "@/lib/csp/trustedTypes";

/**
 * The first script the page runs: installs the Trusted Types default
 * policy (src/lib/csp/trustedTypes.ts) before Next.js's runtime loads its
 * chunks. Next.js writes it into <head> of the server's HTML, once; it
 * does so for the error shell too, which a page that calls notFound()
 * gets and which has none of the root layout's own head. Renders nothing.
 */
export function TrustedTypesScript({ nonce }: { nonce: string | undefined }) {
  // Next.js calls this at every flush of the stream; the script goes into the first.
  const written = useRef(false);
  useServerInsertedHTML(() => {
    if (written.current) {
      return null;
    }
    written.current = true;
    return <script nonce={nonce} dangerouslySetInnerHTML={{ __html: trustedTypesBootstrap() }} />;
  });
  return null;
}
