/**
 * The animated toast list (ToastList.tsx, with the motion library) as a
 * chunk of its own: fetched once, when a toast first has to be shown.
 */

import { useEffect, useState, type ReactNode } from "react";

import type { ToastListProps } from "./ToastList";

type RenderToastList = (props: ToastListProps) => ReactNode;

let loaded: RenderToastList | null = null;

/** Fetches the list (once). */
export async function loadToastList(): Promise<RenderToastList> {
  loaded ??= (await import("./ToastList")).renderToastList;
  return loaded;
}

/**
 * Renders the list once it is needed and has arrived, else null. A failed
 * fetch (offline) is tried again with the next toast.
 */
export function useToastList(isNeeded: boolean): RenderToastList | null {
  const [render, setRender] = useState<RenderToastList | null>(() => loaded);
  useEffect(() => {
    if (!isNeeded || render !== null) {
      return;
    }
    let isCurrent = true;
    loadToastList().then(
      (renderList) => {
        if (isCurrent) {
          setRender(() => renderList);
        }
      },
      () => undefined,
    );
    return () => {
      isCurrent = false;
    };
  }, [isNeeded, render]);
  return render;
}
