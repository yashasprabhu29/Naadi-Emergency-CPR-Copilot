// Line icons drawn on a 24 px grid. Decorative by default.
function Icon({ children, size = 18, className = "" }) {
  return (
    <svg
      className={`icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export const UploadIcon = (p) => (
  <Icon {...p}><path d="M12 15V4" /><path d="m7 9 5-5 5 5" /><path d="M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3" /></Icon>
);
export const FileAudioIcon = (p) => (
  <Icon {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M9 13v3" /><path d="M12 11v7" /><path d="M15 13v3" /></Icon>
);
export const CheckIcon = (p) => (
  <Icon {...p}><path d="m5 12.5 4.5 4.5L19 7.5" /></Icon>
);
export const AlertIcon = (p) => (
  <Icon {...p}><path d="M10.3 4.1 2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 4.1a2 2 0 0 0-3.4 0z" /><path d="M12 9.5v4" /><path d="M12 17h.01" /></Icon>
);
export const ArrowRightIcon = (p) => (
  <Icon {...p}><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></Icon>
);
export const RefreshIcon = (p) => (
  <Icon {...p}><path d="M20 11a8 8 0 0 0-14.3-4.9L4 8" /><path d="M4 4v4h4" /><path d="M4 13a8 8 0 0 0 14.3 4.9L20 16" /><path d="M20 20v-4h-4" /></Icon>
);
export const PersonDownIcon = (p) => (
  <Icon {...p}><circle cx="6" cy="9" r="2" /><path d="M9 12h11" /><path d="M10 12l2-3h4" /><path d="M3 17h18" /></Icon>
);
export const LungsIcon = (p) => (
  <Icon {...p}><path d="M12 4v8" /><path d="M12 12c-1 1-2 1.5-3 1.5" /><path d="M12 12c1 1 2 1.5 3 1.5" /><path d="M8.5 7C6 7 4 11 4 15.5 4 18 5 19 6.5 19S9 18 9 16V9.5" /><path d="M15.5 7C18 7 20 11 20 15.5 20 18 19 19 17.5 19S15 18 15 16V9.5" /></Icon>
);
export const ShieldIcon = (p) => (
  <Icon {...p}><path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z" /><path d="m9 12 2 2 4-4" /></Icon>
);
export const PhoneIcon = (p) => (
  <Icon {...p}><path d="M5 4h3l2 5-2.5 1.5a11 11 0 0 0 6 6L15 14l5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" /></Icon>
);

// Naadi mark: a pulse trace inside a rounded square.
export function NaadiMark({ size = 30 }) {
  return (
    <svg className="naadi-mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="7" fill="#E5484D" />
      <path
        className="naadi-mark__trace"
        d="M4 17h6l2.5-6 4 12 3-9 1.5 3H28"
        fill="none"
        stroke="#FFF7F5"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength="100"
      />
    </svg>
  );
}
