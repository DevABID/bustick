import React, { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import Icon from "./Icons";

const LINKS = [
  { to: "/", label: "Book tickets", icon: Icon.Bus, end: true },
  { to: "/check-ticket", label: "Find my ticket", icon: Icon.Ticket },
  { to: "/return-ticket", label: "Return ticket", icon: Icon.Return },
  { to: "/support", label: "Help", icon: Icon.Help },
];

export function Logo() {
  return (
    <Link to="/" className="logo" aria-label="BusTick home">
      <span className="logo-mark"><Icon.Bus size={20} /></span>
      BusTick
    </Link>
  );
}

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => setOpen(false), [pathname]);

  return (
    <header className="nav">
      <div className="container nav-inner">
        <Logo />
        <nav aria-label="Main">
          <div id="main-menu" className={`nav-links ${open ? "open" : ""}`}>
            {LINKS.map(({ to, label, icon: I, end }) => (
              <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                <I size={18} /> {label}
              </NavLink>
            ))}
          </div>
        </nav>
        <button className="nav-toggle" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open}
          aria-controls="main-menu" onClick={() => setOpen(!open)}>
          {open ? <Icon.X /> : <Icon.Menu />}
        </button>
      </div>
    </header>
  );
}
