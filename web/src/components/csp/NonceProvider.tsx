"use client";

/**
 * The page's Content Security Policy nonce, for the <style> elements that
 * client components render (NoncedStyle). The browser keeps the policy of
 * the document's first response, so the nonce of a later server render
 * (`router.refresh()`) would not match: the provider keeps the first one.
 */

import { createContext, useContext, useState, type ReactNode } from "react";

const NonceContext = createContext<string | undefined>(undefined);

export function NonceProvider({ nonce, children }: { nonce: string | undefined; children: ReactNode }) {
  const [documentNonce] = useState(nonce);
  return <NonceContext value={documentNonce}>{children}</NonceContext>;
}

/** The document's nonce; undefined outside a request (tests, static rendering). */
export function useNonce(): string | undefined {
  return useContext(NonceContext);
}
