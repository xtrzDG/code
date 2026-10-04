"use client";

/**
 * The phone's compact chrome (below lg): a page's title lives in the top
 * bar, its description behind an (i), its live status as a dot there, and
 * its primary action as a floating button above the tab bar. The shell
 * (ShellFrame) provides the slots; PageHeader, LiveStatus and pages fill
 * them:
 *
 *     usePhoneFab({ label: t("bookings.newBooking"), icon: IconPlus, onClick: openForm });
 *
 * Outside the shell (sign-in, the business list) there are no slots and
 * pages keep their full headers on every screen.
 */

import {
  createContext,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type ComponentType,
  type ReactNode,
} from "react";

import {
  ChromeStore,
  EMPTY_SNAPSHOT,
  type ChromeDescription,
  type ChromeLevel,
  type ChromeLive,
  type ChromeSnapshot,
} from "@/lib/phoneChrome";

import type { IconProps } from "../icons";

type FabIcon = ComponentType<IconProps>;
type Store = ChromeStore<ReactNode, FabIcon>;
export type PhoneChromeSnapshot = ChromeSnapshot<ReactNode, FabIcon>;

interface PhoneChromeValue {
  store: Store;
  /** The top bar shows the title, the (i) and the live dot. */
  hasTopBar: boolean;
  /** The tab bar carries a floating button. */
  hasFabSlot: boolean;
}

const PhoneChromeContext = createContext<PhoneChromeValue | null>(null);

export function PhoneChromeProvider({
  hasTopBar,
  hasFabSlot,
  children,
}: {
  hasTopBar: boolean;
  hasFabSlot: boolean;
  children: ReactNode;
}) {
  const [store] = useState<Store>(() => new ChromeStore<ReactNode, FabIcon>());
  const value = useMemo(() => ({ store, hasTopBar, hasFabSlot }), [store, hasTopBar, hasFabSlot]);
  return <PhoneChromeContext.Provider value={value}>{children}</PhoneChromeContext.Provider>;
}

/** The slots of the shell, or null outside it. */
export function usePhoneChrome(): Omit<PhoneChromeValue, "store"> | null {
  const value = useContext(PhoneChromeContext);
  return value ? { hasTopBar: value.hasTopBar, hasFabSlot: value.hasFabSlot } : null;
}

const getEmpty = () => EMPTY_SNAPSHOT;
const ignore = () => () => undefined;

/** What the bars show now (for the top bar, the tab bar and the page's padding). */
export function usePhoneChromeSnapshot(): PhoneChromeSnapshot {
  const value = useContext(PhoneChromeContext);
  return useSyncExternalStore(value?.store.subscribe ?? ignore, value?.store.getSnapshot ?? getEmpty, getEmpty);
}

type Entry = Parameters<Store["set"]>[1];

/** Keeps `entry` registered while the component is on screen (null registers nothing). */
function useEntry(entry: Entry | null): void {
  const value = useContext(PhoneChromeContext);
  const id = useId();
  const store = value?.store;
  useEffect(() => {
    if (!store || !entry) {
      return;
    }
    store.set(id, entry);
    return () => store.remove(id);
  }, [store, id, entry]);
}

/** The page's description, for the top bar's (i). */
export function usePhoneDescription(level: ChromeLevel, description: ChromeDescription<ReactNode> | null): void {
  const title = description?.title;
  const text = description?.text;
  const entry = useMemo<Entry | null>(
    () => (title !== undefined && text ? { level, description: { title, text } } : null),
    [level, title, text],
  );
  useEntry(entry);
}

/** The page's live status, for the top bar's dot. */
export function usePhoneLive(level: ChromeLevel, live: ChromeLive | null): void {
  const updatedAt = live?.updatedAt;
  const isFetching = live?.isFetching ?? false;
  const entry = useMemo<Entry | null>(
    () => (updatedAt === undefined ? null : { level, live: { updatedAt, isFetching } }),
    [level, updatedAt, isFetching],
  );
  useEntry(entry);
}

export interface PhoneFabAction {
  label: string;
  icon: FabIcon;
  onClick: () => void;
  /** The action opens a dialog (announced as such). */
  opensDialog?: boolean;
}

/**
 * The page's primary action as the floating button (the deepest level
 * wins); `null` hides a section's button on a page with its own way to act.
 */
export function usePhoneFab(level: ChromeLevel, action: PhoneFabAction | null | undefined): void {
  const onClick = useRef(action?.onClick);
  useEffect(() => {
    onClick.current = action?.onClick;
  });
  const isNone = action === null;
  const label = action?.label;
  const icon = action?.icon;
  const opensDialog = action?.opensDialog;
  const entry = useMemo<Entry | null>(() => {
    if (isNone) {
      return { level, fab: null };
    }
    if (label === undefined || icon === undefined) {
      return null;
    }
    return { level, fab: { label, icon, opensDialog, run: () => onClick.current?.() } };
  }, [level, isNone, label, icon, opensDialog]);
  useEntry(entry);
}
