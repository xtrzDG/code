"use client";

/**
 * The help of the page shown: the cabinet's frame puts a "?" here for the
 * page that is open (components/help/HelpLink), and the page's own header
 * (PageHeader) and the phone's top bar show it beside the title. Outside
 * the frame there is none.
 */

import { createContext, useContext, type ReactNode } from "react";

const PageHelpContext = createContext<ReactNode>(null);

export function PageHelpProvider({ help, children }: { help: ReactNode; children: ReactNode }) {
  return <PageHelpContext.Provider value={help}>{children}</PageHelpContext.Provider>;
}

export function usePageHelp(): ReactNode {
  return useContext(PageHelpContext);
}
