import React from "react";
import { Link } from "react-router-dom";
import { Logo } from "./Navbar";

export default function Footer() {
  return (
    <footer className="footer no-print">
      <div className="container">
        <div className="footer-grid">
          <div className="stack gap-12">
            <Logo />
            <p style={{ maxWidth: 360 }}>Book intercity bus tickets in minutes. Choose your seat, pay securely and get your e-ticket by email.</p>
          </div>
          <div className="stack gap-8">
            <b style={{ color: "#fff" }}>Manage</b>
            <Link to="/check-ticket">Find my ticket</Link>
            <Link to="/return-ticket">Return a ticket</Link>
          </div>
          <div className="stack gap-8">
            <b style={{ color: "#fff" }}>Help</b>
            <Link to="/support">FAQ &amp; support</Link>
            <Link to="/support#policy">Cancellation policy</Link>
            <Link to="/support#contact">Contact us</Link>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} BusTick</span>
          <span>Secure payments by SSLCommerz</span>
        </div>
      </div>
    </footer>
  );
}
