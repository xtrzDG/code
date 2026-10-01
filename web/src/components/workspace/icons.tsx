/**
 * Extra outline icons of the channels, billing, settings and admin pages
 * (same 24×24 stroke style as components/icons.tsx).
 */

import type { SVGProps } from "react";

export type IconProps = SVGProps<SVGSVGElement>;

function Icon({ children, ...props }: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

export const IconCopy = (props: IconProps) => (
  <Icon {...props}>
    <rect x="8.5" y="8.5" width="11.5" height="11.5" rx="2" />
    <path d="M15.5 8.5V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7.5a2 2 0 002 2h2.5" />
  </Icon>
);

export const IconDownload = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M4.5 19.5h15" />
  </Icon>
);

export const IconRefresh = (props: IconProps) => (
  <Icon {...props}>
    <path d="M19.5 12a7.5 7.5 0 01-13 5.1M4.5 12a7.5 7.5 0 0113-5.1M17.5 3.5v3.6h-3.6M6.5 20.5v-3.6h3.6" />
  </Icon>
);

export const IconPhone = (props: IconProps) => (
  <Icon {...props}>
    <path d="M6.6 3.5h2.6l1.4 4-2 1.3a11 11 0 006.6 6.6l1.3-2 4 1.4v2.6a2 2 0 01-2.2 2A16.5 16.5 0 014.6 5.7a2 2 0 012-2.2z" />
  </Icon>
);

export const IconSend = (props: IconProps) => (
  <Icon {...props}>
    <path d="M20.5 3.5L3.5 10.5l6.5 2.5 2.5 6.5zM10 13l4.5-4.5" />
  </Icon>
);

export const IconWhatsApp = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 20l1.3-4A8.5 8.5 0 1112 20.5a8.4 8.4 0 01-4-1z" />
    <path d="M9 8.5c0 3.2 2.3 6 5.5 6.5l1-1.5-1.8-1-1 .8a4.5 4.5 0 01-2.5-2.5l.8-1-1-1.8z" />
  </Icon>
);

export const IconInstagram = (props: IconProps) => (
  <Icon {...props}>
    <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
    <circle cx="12" cy="12" r="3.8" />
    <path d="M17 7h.01" />
  </Icon>
);

export const IconMessenger = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 3.5c-4.8 0-8.5 3.5-8.5 8 0 2.5 1.1 4.6 3 6v3l2.8-1.5c.9.3 1.8.4 2.7.4 4.8 0 8.5-3.5 8.5-8s-3.7-7.9-8.5-7.9z" />
    <path d="M7.5 13.5l3-3 2.5 2 3.5-3" />
  </Icon>
);

export const IconWindow = (props: IconProps) => (
  <Icon {...props}>
    <rect x="3" y="4.5" width="18" height="15" rx="2" />
    <path d="M3 8.5h18M6.5 6.5h.01M9 6.5h.01M14 15.5h3.5v-3" />
  </Icon>
);

export const IconUsers = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="9" cy="8.5" r="3.5" />
    <path d="M2.5 19.5a6.5 6.5 0 0113 0M16 5a3.5 3.5 0 010 7M18 14.5a5.5 5.5 0 013.5 5" />
  </Icon>
);

export const IconBell = (props: IconProps) => (
  <Icon {...props}>
    <path d="M6 16.5V11a6 6 0 0112 0v5.5l1.5 2h-15zM10 20.5a2 2 0 004 0" />
  </Icon>
);

export const IconFile = (props: IconProps) => (
  <Icon {...props}>
    <path d="M13.5 3.5H7a2 2 0 00-2 2v13a2 2 0 002 2h10a2 2 0 002-2V9z" />
    <path d="M13.5 3.5V9H19M8.5 13h7M8.5 16.5h5" />
  </Icon>
);

export const IconList = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 6.5h11M9 12h11M9 17.5h11M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01" />
  </Icon>
);

export const IconSearch = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M16 16l4 4" />
  </Icon>
);

export const IconPause = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 5.5v13M15 5.5v13" />
  </Icon>
);

export const IconPlay = (props: IconProps) => (
  <Icon {...props}>
    <path d="M7.5 5l11 7-11 7z" />
  </Icon>
);

export const IconLink = (props: IconProps) => (
  <Icon {...props}>
    <path d="M10 14a4.5 4.5 0 006.4 0l3-3a4.5 4.5 0 00-6.4-6.4l-1 1M14 10a4.5 4.5 0 00-6.4 0l-3 3a4.5 4.5 0 006.4 6.4l1-1" />
  </Icon>
);
