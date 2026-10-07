/** Icons of the cabinet sections and the things they hold (people, places, tools, themes). */

import { Icon, type IconProps } from "./Icon";

export const IconGlobe = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z" />
  </Icon>
);

export const IconLogout = (props: IconProps) => (
  <Icon {...props}>
    <path d="M15 4h3a2 2 0 012 2v12a2 2 0 01-2 2h-3M10 16l-4-4 4-4M6 12h10" />
  </Icon>
);

export const IconBuilding = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 21V5a2 2 0 012-2h8a2 2 0 012 2v16M16 9h2a2 2 0 012 2v10M3 21h18M8 7h4M8 11h4M8 15h4" />
  </Icon>
);

export const IconClipboard = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 4h6v3H9zM9 5H6a1 1 0 00-1 1v14a1 1 0 001 1h12a1 1 0 001-1V6a1 1 0 00-1-1h-3M9 12l2 2 4-4" />
  </Icon>
);

export const IconGauge = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 18a8 8 0 1116 0M12 18l4-6" />
    <circle cx="12" cy="18" r="1" />
  </Icon>
);

export const IconChat = (props: IconProps) => (
  <Icon {...props}>
    <path d="M5 18l-1.5 3 4-1.5A8.5 8.5 0 1012 3.5 8.5 8.5 0 003.5 12c0 2.2.6 4.2 1.5 6z" />
  </Icon>
);

export const IconCalendar = (props: IconProps) => (
  <Icon {...props}>
    <rect x="3.5" y="5" width="17" height="15.5" rx="2" />
    <path d="M3.5 10h17M8 3v4M16 3v4" />
  </Icon>
);

export const IconInbox = (props: IconProps) => (
  <Icon {...props}>
    <path d="M3.5 13.5l2.5-8h12l2.5 8v5a1.5 1.5 0 01-1.5 1.5H5a1.5 1.5 0 01-1.5-1.5zM3.5 13.5H8l1.5 2.5h5l1.5-2.5h4.5" />
  </Icon>
);

export const IconHandoff = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="9" cy="8" r="3.5" />
    <path d="M3 20c.6-3.4 3-5.5 6-5.5 1.5 0 2.8.5 3.8 1.4M15 14h6M18 11l3 3-3 3" />
  </Icon>
);

export const IconBook = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 6.5C10.5 5 8 4.5 4 4.5v14c4 0 6.5.5 8 2 1.5-1.5 4-2 8-2v-14c-4 0-6.5.5-8 2zM12 6.5v14" />
  </Icon>
);

export const IconSparkles = (props: IconProps) => (
  <Icon {...props}>
    <path d="M10 4l1.6 4.4L16 10l-4.4 1.6L10 16l-1.6-4.4L4 10l4.4-1.6zM17.5 14l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z" />
  </Icon>
);

export const IconPlug = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 3v4M15 3v4M7 7h10v4a5 5 0 01-10 0zM12 16v5" />
  </Icon>
);

export const IconCard = (props: IconProps) => (
  <Icon {...props}>
    <rect x="3" y="5.5" width="18" height="13" rx="2" />
    <path d="M3 10h18M7 15h3" />
  </Icon>
);

export const IconSettings = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="3" />
    <path d="M12 2.5v2.2M12 19.3v2.2M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6" />
  </Icon>
);

export const IconShield = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 3l7.5 3v5.5c0 4.6-3.2 8.3-7.5 9.5-4.3-1.2-7.5-4.9-7.5-9.5V6z" />
    <path d="M9 12l2 2 4-4" />
  </Icon>
);

export const IconMoon = (props: IconProps) => (
  <Icon {...props}>
    <path d="M20 14.5A8.5 8.5 0 019.5 4a8.5 8.5 0 1010.5 10.5z" />
  </Icon>
);

export const IconSun = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4L6 18M18 6l1.4-1.4" />
  </Icon>
);

export const IconMonitor = (props: IconProps) => (
  <Icon {...props}>
    <rect x="3" y="4" width="18" height="12.5" rx="2" />
    <path d="M8.5 20.5h7M12 16.5v4" />
  </Icon>
);

export const IconPhone = (props: IconProps) => (
  <Icon {...props}>
    <path d="M5 4h3.5l1.8 4.5-2.3 1.4a11 11 0 005.1 5.1l1.4-2.3L19 14.5V18a2 2 0 01-2 2A14 14 0 013 6a2 2 0 012-2z" />
  </Icon>
);

export const IconWrench = (props: IconProps) => (
  <Icon {...props}>
    <path d="M14.5 6.5a4 4 0 015.2 5.2l-1.5-1.5-2.3.6-.6 2.3 1.5 1.5a4 4 0 01-5.2-5.2L4 17.5 6.5 20l7.6-7.6" />
  </Icon>
);

export const IconRocket = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 15l-3-3c1.5-4.5 4.5-7.5 10-8-.5 5.5-3.5 8.5-8 10zM9 12l-4 .5L7.5 9H11M12 15l-.5 4 3.5-2.5V13" />
    <path d="M6 18c-1 .5-1.5 1.5-2 3 1.5-.5 2.5-1 3-2" />
  </Icon>
);

export const IconFlask = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 3h6M10 3v6l-5.5 9.5A1.7 1.7 0 006 21h12a1.7 1.7 0 001.5-2.5L14 9V3M7.5 15h9" />
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

/** Encryption keys (the platform admin's key ring). */
export const IconKey = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="8" cy="15" r="4" />
    <path d="M10.8 12.2L20 3M16.5 6.5l2.5 2.5M14 9l2 2" />
  </Icon>
);

/** The platform's health (the admin's System page): a pulse line. */
export const IconPulse = (props: IconProps) => (
  <Icon {...props}>
    <path d="M3 12h4l2.5-6 4 12 2.5-6H21" />
  </Icon>
);
