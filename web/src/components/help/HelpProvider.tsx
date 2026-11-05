"use client";

/**
 * The article drawer of the cabinet's frame: `useHelpDrawer().open(slug)`
 * shows an article over the page (the "?" beside a page's title, a tip's
 * "Read the guide"); links between articles open in place with a way back.
 * Outside the frame there is no drawer and help links lead to /help.
 */

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { HelpDrawer } from "./HelpDrawer";

interface HelpDrawerApi {
  open: (slug: string) => void;
}

const HelpDrawerContext = createContext<HelpDrawerApi | null>(null);

export function useHelpDrawer(): HelpDrawerApi | null {
  return useContext(HelpDrawerContext);
}

export function HelpProvider({ children }: { children: ReactNode }) {
  // The articles opened, the shown one last; empty while the drawer is closed.
  const [trail, setTrail] = useState<string[]>([]);
  const open = useCallback((slug: string) => setTrail([slug]), []);
  const value = useMemo(() => ({ open }), [open]);

  return (
    <HelpDrawerContext.Provider value={value}>
      {children}
      <HelpDrawer
        slug={trail.at(-1) ?? null}
        canGoBack={trail.length > 1}
        onOpen={(slug) => setTrail((current) => (current.at(-1) === slug ? current : [...current, slug]))}
        onBack={() => setTrail((current) => current.slice(0, -1))}
        onClose={() => setTrail([])}
      />
    </HelpDrawerContext.Provider>
  );
}
