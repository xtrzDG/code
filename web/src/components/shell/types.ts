import type { ComponentType } from "react";

import type { IconProps } from "../icons";

/** One link of the cabinet's navigation, as the shell renders it. */
interface ShellLink {
  href: string;
  label: string;
  isActive: boolean;
  /** A number waiting there (open handoffs, new requests); 0 for none. */
  badge?: number;
  /** Loads the page's first data when the pointer or the focus reaches the link. */
  onPrefetch?: () => void;
}

/** A page inside a section, listed under it in the sidebar. */
export interface ShellSubLink extends ShellLink {
  /** Listed under the "Advanced" disclosure. */
  isAdvanced?: boolean;
}

/** A section of the sidebar (and, on phones, of the tab bar or "More"). */
export interface ShellNavItem extends ShellLink {
  key: string;
  icon: ComponentType<IconProps>;
  /** Its pages, shown under it in the sidebar while it is open. */
  pages?: readonly ShellSubLink[];
  /** After the main list, set apart (platform admin). */
  secondary?: boolean;
  /** One of the phone tab bar's places (the rest go under "More"). */
  inTabBar?: boolean;
  /** Its name in the tab bar when `label` has a word too long for it. */
  tabLabel?: string;
}
