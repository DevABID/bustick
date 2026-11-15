import React from "react";

// Stroke icons (Lucide-style, MIT-compatible shapes drawn by hand). Usage: <Icon.Bus size={20} />
const make = (paths) =>
  function SvgIcon({ size = 20, strokeWidth = 2, ...props }) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
        {paths}
      </svg>
    );
  };

const Icon = {
  Bus: make(<><path d="M8 6v6M16 6v6M2 12h20" /><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3" /><circle cx="7" cy="18" r="2" /><path d="M9 18h5" /><circle cx="16" cy="18" r="2" /></>),
  Search: make(<><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></>),
  Ticket: make(<><path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z" /><path d="M13 5v2M13 17v2M13 11v2" /></>),
  Return: make(<><path d="M9 14 4 9l5-5" /><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11" /></>),
  Help: make(<><circle cx="12" cy="12" r="10" /><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01" /></>),
  MapPin: make(<><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" /></>),
  Calendar: make(<><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></>),
  Clock: make(<><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>),
  Swap: make(<><path d="m16 3 4 4-4 4" /><path d="M20 7H4" /><path d="m8 21-4-4 4-4" /><path d="M4 17h16" /></>),
  Arrow: make(<><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></>),
  Check: make(<path d="M20 6 9 17l-5-5" />),
  CheckCircle: make(<><circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" /></>),
  X: make(<><path d="M18 6 6 18M6 6l12 12" /></>),
  Alert: make(<><circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" /></>),
  Menu: make(<><path d="M4 6h16M4 12h16M4 18h16" /></>),
  Shield: make(<><path d="M20 13c0 5-3.5 7.5-7.7 9a1 1 0 0 1-.6 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.2-2.7a1.2 1.2 0 0 1 1.6 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1Z" /><path d="m9 12 2 2 4-4" /></>),
  Mail: make(<><rect x="2" y="4" width="20" height="16" rx="2" /><path d="m22 7-10 6L2 7" /></>),
  Phone: make(<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2Z" />),
  User: make(<><circle cx="12" cy="8" r="4" /><path d="M20 21a8 8 0 0 0-16 0" /></>),
  Card: make(<><rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20" /></>),
  Download: make(<><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m7 10 5 5 5-5M12 15V3" /></>),
  Printer: make(<><path d="M6 9V2h12v7" /><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" /><rect x="6" y="14" width="12" height="8" /></>),
  Seat: make(<><path d="M7 18v-6a5 5 0 0 1 10 0v6" /><path d="M5 21v-3a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v3" /><path d="M5 12v4M19 12v4" /></>),
  Snow: make(<><path d="M2 12h20M12 2v20M20 16l-4-4 4-4M4 8l4 4-4 4M16 4l-4 4-4-4M8 20l4-4 4 4" /></>),
  Zap: make(<path d="M4 14a1 1 0 0 1-.8-1.6l9.9-10.2a.5.5 0 0 1 .9.5l-1.9 6A1 1 0 0 0 13 10h7a1 1 0 0 1 .8 1.6l-9.9 10.2a.5.5 0 0 1-.9-.5l1.9-6A1 1 0 0 0 11 14z" />),
  Wheel: make(<><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="2" /><path d="M12 14v8M10.3 11 3.2 7.5M13.7 11l7.1-3.5" /></>),
  Sort: make(<><path d="m3 16 4 4 4-4M7 20V4M21 8l-4-4-4 4M17 4v16" /></>),
  Lock: make(<><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></>),
  Timer: make(<><path d="M10 2h4M12 14l3-3" /><circle cx="12" cy="14" r="8" /></>),
};

export default Icon;
