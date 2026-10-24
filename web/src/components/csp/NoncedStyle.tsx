"use client";

/**
 * A <style> element the Content Security Policy accepts: it carries the
 * page's nonce. For rules that must hold at the first paint and depend on
 * data (the hosted chat page's accent colour), where a class cannot name
 * the value. The CSS must be built from validated values only.
 */

import { useNonce } from "./NonceProvider";

export function NoncedStyle({ css }: { css: string }) {
  const nonce = useNonce();
  return <style nonce={nonce}>{css}</style>;
}
