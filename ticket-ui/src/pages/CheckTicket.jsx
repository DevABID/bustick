import React, { useState } from "react";
import { Link } from "react-router-dom";
import api, { API_URL, errorMessage } from "../api";
import Icon from "../components/Icons";
import { money, prettyDate, time12 } from "../format";

const STATUS_BADGE = { Paid: "badge-green", Pending: "badge-amber", Cancelled: "badge-red", Expired: "badge-gray" };

export function LookupForm({ onSubmit, busy, submitLabel, danger }) {
  const [pnr, setPnr] = useState("");
  const [email, setEmail] = useState("");
  return (
    <form className="stack gap-16" onSubmit={(e) => { e.preventDefault(); onSubmit(pnr.trim().toUpperCase(), email.trim()); }}>
      <div className="field">
        <label htmlFor="pnr">PNR number</label>
        <div className="input-wrap"><Icon.Ticket size={18} />
          <input id="pnr" className="input mono" placeholder="e.g. BR7K9X22" maxLength={10} required value={pnr}
            onChange={(e) => setPnr(e.target.value.toUpperCase())} />
        </div>
      </div>
      <div className="field">
        <label htmlFor="lemail">Email used for booking</label>
        <div className="input-wrap"><Icon.Mail size={18} />
          <input id="lemail" type="email" className="input" placeholder="you@example.com" required value={email}
            onChange={(e) => setEmail(e.target.value)} />
        </div>
      </div>
      <button className={`btn btn-lg btn-block ${danger ? "btn-danger" : "btn-primary"}`} disabled={busy || !pnr || !email}>
        {busy ? <span className="spinner" /> : null} {submitLabel}
      </button>
    </form>
  );
}

export default function CheckTicket() {
  const [busy, setBusy] = useState(false);
  const [ticket, setTicket] = useState(null);
  const [error, setError] = useState("");

  const lookup = async (pnr, email) => {
    setBusy(true); setError(""); setTicket(null);
    try {
      const { data } = await api.get("/tickets/lookup/", { params: { pnr, email } });
      setTicket(data);
    } catch (e) {
      setError(errorMessage(e, "No ticket matches that PNR and email."));
    } finally { setBusy(false); }
  };

  return (
    <main className="page">
      <div className="container narrow stack gap-24">
        <div className="stack gap-8">
          <h1 style={{ fontSize: 30 }}>Find my ticket</h1>
          <p className="muted">Enter the PNR from your e-ticket and the email you booked with.</p>
        </div>
        <div className="card card-pad"><LookupForm onSubmit={lookup} busy={busy} submitLabel="Find ticket" /></div>
        {error && <div className="alert alert-error" role="alert"><Icon.Alert size={18} /> {error}</div>}

        {ticket && (
          <div className="card ticket">
            <div className="ticket-head">
              <div className="stack gap-4"><span className="label" style={{ color: "#94a3b8" }}>PNR</span><h2 className="mono">{ticket.pnr_number}</h2></div>
              <span className={`badge ${STATUS_BADGE[ticket.status] || "badge-gray"}`}>{ticket.status}</span>
            </div>
            <div className="ticket-route">
              <div className="stack gap-4"><span className="label">From</span><span className="city">{ticket.from_city}</span></div>
              <Icon.Bus size={28} style={{ color: "#94a3b8" }} />
              <div className="stack gap-4" style={{ textAlign: "right" }}><span className="label">To</span><span className="city">{ticket.to_city}</span></div>
            </div>
            <div className="ticket-cut" />
            <div className="ticket-grid">
              <div className="stack gap-4"><span className="label">Date</span><b className="bold">{prettyDate(ticket.date)}</b></div>
              <div className="stack gap-4"><span className="label">Departure</span><b className="bold">{time12(ticket.departure_time)}</b></div>
              <div className="stack gap-4"><span className="label">Seat</span><b className="bold">{ticket.seat_number}</b></div>
              <div className="stack gap-4"><span className="label">Fare</span><b className="bold">{money(ticket.price)}</b></div>
              <div className="stack gap-4"><span className="label">Passenger</span><b className="bold">{ticket.customer_name}</b></div>
              <div className="stack gap-4"><span className="label">Bus</span><b className="bold">{ticket.bus_name}</b></div>
              <div className="stack gap-4"><span className="label">Class</span><b className="bold">{ticket.bus_type}</b></div>
            </div>
            {ticket.tran_id && (
              <div className="card-pad row gap-12 wrap no-print" style={{ borderTop: "1px solid var(--line)" }}>
                <a className="btn btn-dark" href={`${API_URL}/api/payments/${ticket.tran_id}/ticket.pdf`}><Icon.Download size={18} /> Download PDF</a>
                <button className="btn btn-outline" onClick={() => window.print()}><Icon.Printer size={18} /> Print</button>
                <Link className="btn btn-ghost" to="/return-ticket">Return this ticket</Link>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
