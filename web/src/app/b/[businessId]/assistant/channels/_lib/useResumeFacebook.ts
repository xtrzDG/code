"use client";

import { useEffect, useRef } from "react";

import { resumedChannel, withoutResume, type MetaChannel } from "./metaSignIn";

/**
 * After the page was loaded again so that Facebook may open (the connect
 * dialog asked for it: lib/metaSignInPages.ts), opens `kind`'s dialog once
 * and takes the marker out of the address (a reload or a shared link must
 * not open it again; a null state keeps Next's router in step).
 */
export function useResumeFacebook(kind: MetaChannel | null, isAllowed: boolean, open: (kind: MetaChannel) => void): void {
  const openRef = useRef(open);
  useEffect(() => {
    openRef.current = open;
  });

  useEffect(() => {
    if (!isAllowed || kind === null || resumedChannel(window.location.search) !== kind) {
      return;
    }
    window.history.replaceState(null, "", withoutResume(window.location.href));
    openRef.current(kind);
  }, [kind, isAllowed]);
}
