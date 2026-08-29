// A small, consistent stroke-icon set (24x24, Feather/Lucide-style) — replaces
// emoji throughout the app so the UI reads as a real product, not a prototype.
import type { SVGProps } from "react";

function Icon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      width={props.width ?? 18}
      height={props.height ?? 18}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    />
  );
}

export const HomeIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M3 11.5 12 4l9 7.5" />
    <path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9" />
  </Icon>
);

export const FolderIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M3 6a1 1 0 0 1 1-1h4.5l2 2.2H20a1 1 0 0 1 1 1V18a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z" />
  </Icon>
);

export const FileIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M7 3.5h7L19 8v12.5a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1v-16a1 1 0 0 1 1-1Z" />
    <path d="M14 3.5V8h5" />
    <path d="M9 13h6M9 16.5h6" />
  </Icon>
);

export const ChatIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M4 5.5h16a1 1 0 0 1 1 1V15a1 1 0 0 1-1 1H9l-4.4 3.3A.6.6 0 0 1 3.5 18.8V16.5H4a1 1 0 0 1-1-1V6.5a1 1 0 0 1 1-1Z" />
  </Icon>
);

export const SparkleIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M12 3.5 13.6 9.4 19.5 11 13.6 12.6 12 18.5 10.4 12.6 4.5 11 10.4 9.4Z" />
    <path d="M19 4v3M17.5 5.5h3" />
  </Icon>
);

export const SearchIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="m20 20-4.3-4.3" />
  </Icon>
);

export const BellIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M6 10a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 14 6 10Z" />
    <path d="M10 19a2 2 0 0 0 4 0" />
  </Icon>
);

export const UploadIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M12 15.5V4M8 8l4-4 4 4" />
    <path d="M4.5 15.5V19a1 1 0 0 0 1 1h13a1 1 0 0 0 1-1v-3.5" />
  </Icon>
);

export const PlusIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M12 5v14M5 12h14" />
  </Icon>
);

export const SendIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M4.5 12 20 4l-6 16-3-6.5Z" />
    <path d="M20 4 10.5 13.5" />
  </Icon>
);

export const CheckIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="m5 13 4.5 4.5L19 8" />
  </Icon>
);

export const XIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="m6 6 12 12M18 6 6 18" />
  </Icon>
);

export const MenuIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Icon>
);

export const ClockIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8" />
    <path d="M12 8v4.5l3 2" />
  </Icon>
);

export const WarningIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M12 4 21 19H3Z" />
    <path d="M12 10v3.5" />
    <circle cx="12" cy="16.3" r="0.4" fill="currentColor" stroke="none" />
  </Icon>
);

export const LogOutIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M9 4.5H6a1 1 0 0 0-1 1V18.5a1 1 0 0 0 1 1h3" />
    <path d="M14 8l4.5 4-4.5 4M18.3 12H9.5" />
  </Icon>
);

export const ChevronRightIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="m9 6 6 6-6 6" />
  </Icon>
);

export const SunIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 3v1.6M12 19.4V21M4.6 12H3M21 12h-1.6M6 6l1.1 1.1M17.9 17.9 19 19M6 18l1.1-1.1M17.9 6.1 19 5" />
  </Icon>
);

export const MoonIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M20 14.2A8 8 0 1 1 9.8 4a6.4 6.4 0 0 0 10.2 10.2Z" />
  </Icon>
);

export const LaptopIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <rect x="4" y="5" width="16" height="10.5" rx="1" />
    <path d="M2.5 19.5h19" />
  </Icon>
);

export const RocketIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M12 3c3 1.5 5 5 4.5 9.5L14 15l-4 0-2.5-2.5C8 8 9 4.5 12 3Z" />
    <circle cx="12" cy="9.5" r="1.4" />
    <path d="M9.5 15 8 19l2.2-1M14.5 15 16 19l-2.2-1" />
  </Icon>
);

export const ChartIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}>
    <path d="M4 20V10M11 20V4M18 20v-7" />
    <path d="M3 20h18" />
  </Icon>
);
