/**
 * Extra outline icons of the Knowledge and Assistant sections, drawn like
 * components/icons.tsx (24×24, stroke = currentColor).
 */

import type { IconProps } from "../icons";

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

export const IconQuestion = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.5 9.5a2.5 2.5 0 114 2c-.9.6-1.5 1.2-1.5 2.2M12 16.8v.01" />
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

export const IconUndo = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 14L4 9l5-5M4 9h10.5a5.5 5.5 0 010 11H11" />
  </Icon>
);

export const IconFlask = (props: IconProps) => (
  <Icon {...props}>
    <path d="M9 3h6M10 3v6l-5.5 9.5A1.7 1.7 0 006 21h12a1.7 1.7 0 001.5-2.5L14 9V3M7.5 15h9" />
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
