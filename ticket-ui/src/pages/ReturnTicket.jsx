import React, { useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import Icon from "../components/Icons";
import { LookupForm } from "./CheckTicket";

export default function ReturnTicket() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const submit = async (pnr, email) => {
    if (!window.confirm(`Return ticket ${pnr}? This can't be undone.`)) return;
    setBusy(true); setResult(null);
    try {
      const { data } = await api.post("/tickets/return/", { pnr, email });
      setResult({ ok: true, text: data.message });
    } catch (e) {
      setResult({ ok: false, text: errorMessage(e) });
    } finally { setBusy(false); }
  };

  return (
    <main className="page">
      <div className="container narrow stack gap-24">
        <div className="stack gap-8">
          <h1 style={{ fontSize: 30 }}>Return a ticket</h1>
          <p className="muted">Changed plans? Return your ticket online and get a refund to your original payment method.</p>
        </div>
        <div className="alert alert-info"><Icon.Clock size={18} /> Tickets can be returned up to 12 hours before departure. Each seat is returned separately using its own PNR.</div>
        <div className="card card-pad"><LookupForm onSubmit={submit} busy={busy} submitLabel="Return ticket" danger /></div>
        {result && (
          <div className={`alert ${result.ok ? "alert-success" : "alert-error"}`} role="alert">
            {result.ok ? <Icon.CheckCircle size={18} /> : <Icon.Alert size={18} />} {result.text}
          </div>
        )}
        <p className="small muted center">Need help? <Link to="/support">Visit our help centre</Link></p>
      </div>
    </main>
  );
}
