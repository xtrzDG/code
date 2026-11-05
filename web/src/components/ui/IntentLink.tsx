"use client";

/**
 * A link that fetches its page ahead only once the person may follow it
 * (the pointer over it, a finger on it, the keyboard's focus), not as soon
 * as it is on screen. For the long lists of links that appear at once ("More"
 * on phones, the account menu): their thirty prefetches, each a response to
 * parse, would hold a slow phone's main thread just when the next tap comes
 * (e2e/motion-budget.spec.ts). Next.js's own prefetch takes over from the
 * first sign of intent, so the page is on its way before the tap lands.
 */

import Link from "next/link";
import { useState, type ComponentProps } from "react";

export function IntentLink({ onPointerEnter, onFocus, ...props }: Omit<ComponentProps<typeof Link>, "prefetch">) {
  const [isWanted, setWanted] = useState(false);
  return (
    <Link
      {...props}
      prefetch={isWanted ? null : false}
      onPointerEnter={(event) => {
        setWanted(true);
        onPointerEnter?.(event);
      }}
      onFocus={(event) => {
        setWanted(true);
        onFocus?.(event);
      }}
    />
  );
}
