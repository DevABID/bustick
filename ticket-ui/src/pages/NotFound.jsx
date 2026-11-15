import React from "react";
import { Link } from "react-router-dom";
import Icon from "../components/Icons";

export default function NotFound() {
  return (
    <main className="page">
      <div className="container narrow card empty">
        <div className="icon"><Icon.MapPin size={28} /></div>
        <h1 style={{ fontSize: 26 }}>This page took a wrong turn</h1>
        <p className="muted" style={{ marginTop: 6 }}>The page you're looking for doesn't exist.</p>
        <Link className="btn btn-primary" style={{ marginTop: 20 }} to="/">Back to search</Link>
      </div>
    </main>
  );
}
