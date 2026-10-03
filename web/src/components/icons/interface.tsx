/** Interface icons: actions, arrows, states and documents. */

import { Icon, type IconProps } from "./Icon";

export const IconMenu = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 6h16M4 12h16M4 18h16" />
  </Icon>
);

export const IconX = (props: IconProps) => (
  <Icon {...props}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Icon>
);

export const IconCheck = (props: IconProps) => (
  <Icon {...props}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </Icon>
);

export const IconChevronDown = (props: IconProps) => (
  <Icon {...props}>
    <path d="M6 9l6 6 6-6" />
  </Icon>
);

export const IconChevronRight = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 6l6 6-6 6" />
  </Icon>
);

export const IconArrowLeft = (props: IconProps) => (
  <Icon {...props}>
    <path d="M19 12H5M11 6l-6 6 6 6" />
  </Icon>
);

export const IconArrowRight = (props: IconProps) => (
  <Icon {...props}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Icon>
);

export const IconPlus = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 5v14M5 12h14" />
  </Icon>
);

export const IconTrash = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 002 2h6a2 2 0 002-2l1-12M9 7V4h6v3" />
  </Icon>
);

export const IconAlert = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7.5v5.5M12 16.5v.01" />
  </Icon>
);

export const IconInfo = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5.5M12 7.5v.01" />
  </Icon>
);

export const IconExternal = (props: IconProps) => (
  <Icon {...props}>
    <path d="M14 4h6v6M20 4l-9 9M18 14v4.5a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 014 18.5v-11A1.5 1.5 0 015.5 6H10" />
  </Icon>
);

export const IconClock = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </Icon>
);

export const IconSearch = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M20 20l-4.2-4.2" />
  </Icon>
);

export const IconPencil = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 20h4L19 9a2.8 2.8 0 00-4-4L4 16zM13.5 6.5l4 4" />
  </Icon>
);

export const IconUpload = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 15V4M7.5 8.5L12 4l4.5 4.5M4 15v3.5A1.5 1.5 0 005.5 20h13a1.5 1.5 0 001.5-1.5V15" />
  </Icon>
);

export const IconDownload = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M4.5 19.5h15" />
  </Icon>
);

export const IconLink = (props: IconProps) => (
  <Icon {...props}>
    <path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1" />
  </Icon>
);

export const IconSend = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 12l16-8-6 16-2.5-6.5zM11.5 13.5L20 4" />
  </Icon>
);

export const IconRefresh = (props: IconProps) => (
  <Icon {...props}>
    <path d="M20 11a8 8 0 00-14.5-4.5L4 8M4 4v4h4M4 13a8 8 0 0014.5 4.5L20 16M20 20v-4h-4" />
  </Icon>
);

export const IconUndo = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 14L4 9l5-5M4 9h10.5a5.5 5.5 0 010 11H11" />
  </Icon>
);

export const IconCopy = (props: IconProps) => (
  <Icon {...props}>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M5 15H4.5A1.5 1.5 0 013 13.5v-9A1.5 1.5 0 014.5 3h9A1.5 1.5 0 0115 4.5V5" />
  </Icon>
);

export const IconFile = (props: IconProps) => (
  <Icon {...props}>
    <path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8zM14 3v5h5M9 13h6M9 17h4" />
  </Icon>
);

export const IconList = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 6.5h11M9 12h11M9 17.5h11M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01" />
  </Icon>
);

export const IconXCircle = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9 9l6 6M15 9l-6 6" />
  </Icon>
);

export const IconCheckCircle = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M8 12.5l2.5 2.5L16 9.5" />
  </Icon>
);

export const IconPause = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 5.5v13M15 5.5v13" />
  </Icon>
);

export const IconPlay = (props: IconProps) => (
  <Icon {...props}>
    <path d="M8 5.5v13l10-6.5-10-6.5z" />
  </Icon>
);

export const IconStar = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 3.5l2.6 5.3 5.9.9-4.25 4.1 1 5.8L12 16.85 6.75 19.6l1-5.8L3.5 9.7l5.9-.9z" />
  </Icon>
);

/** A price tag (what the business offers, with prices). */
export const IconTag = (props: IconProps) => (
  <Icon {...props}>
    <path d="M3.5 12.2V4.5a1 1 0 0 1 1-1h7.7a1 1 0 0 1 .7.3l7.6 7.6a1 1 0 0 1 0 1.4l-7.7 7.7a1 1 0 0 1-1.4 0l-7.6-7.6a1 1 0 0 1-.3-.7z" />
    <circle cx="8" cy="8" r="1.4" />
  </Icon>
);

/** Three dots in a row: more actions behind a menu. */
export const IconMore = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="5.5" cy="12" r="1.2" fill="currentColor" />
    <circle cx="12" cy="12" r="1.2" fill="currentColor" />
    <circle cx="18.5" cy="12" r="1.2" fill="currentColor" />
  </Icon>
);
