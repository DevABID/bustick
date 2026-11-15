import React, { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api, { API_URL, errorMessage } from "../api";
import Icon from "../components/Icons";
import { money, prettyDate, seatClassLabel, time12 } from "../format";

export function TicketCard({ payment, bookings }) {
  const s = payment.schedule;
  return (
    <div className="card ticket">
      <div className="ticket-head">
        <div className="stack gap-4">
          <span className="label" style={{ color: "#94a3b8" }}>E-ticket</span>
          <h2>{s.bus_name}</h2>
        </div>
        <span className="badge badge-green"><Icon.Check size={12} /> Paid</span>
      </div>
      <div className="ticket-route">
        <div className="stack gap-4"><span className="label">From</span><span className="city">{s.from_city}</span></div>
        <Icon.Bus size={28} style={{ color: "#94a3b8" }} />
        <div className="stack gap-4" style={{ textAlign: "right" }}><span className="label">To</span><span className="city">{s.to_city}</span></div>
      </div>
      <div className="ticket-cut" />
      <div className="ticket-grid">
        <div className="stack gap-4"><span className="label">Date</span><b className="bold">{prettyDate(s.date)}</b></div>
        <div className="stack gap-4"><span className="label">Departure</span><b className="bold">{time12(s.departure_time)}</b></div>
        <div className="stack gap-4"><span className="label">Class</span><b className="bold">{s.bus_type} · {seatClassLabel(s.seat_type)}</b></div>
        <div className="stack gap-4"><span className="label">Passenger</span><b className="bold">{payment.customer_name}</b></div>
      </div>
      <div className="ticket-cut" />
      <div className="card-pad">
        <div className="kv"><span className="label">Seat</span><span className="label">PNR</span></div>
        {bookings.map((b) => (
          <div key={b.id} className="kv">
            <span className="chip">{b.seat_number}</span>
            <b className="mono bold" style={{ fontSize: 17 }}>{b.pnr_number}</b>
          </div>
        ))}
        <div className="kv"><b className="bold">Total paid</b><b className="price" style={{ color: "#15803d" }}>{money(payment.amount, payment.currency)}</b></div>
      </div>
    </div>
  );
}

export default function Confirmation() {
  const [params] = useSearchParams();
  const tranId = params.get("tran_id");
  const [p, setP] = useState(null);
  const [error, setError] = useState("");
  const tries = useRef(0);

  useEffect(() => {
    if (!tranId) { setError("No booking reference in the link."); return undefined; }
    let timer;
    const poll = () => {
      api.get(`/payments/${tranId}/`).then((r) => {
        setP(r.data);
        // The gateway may confirm a few seconds after redirecting back; keep checking briefly.
        if (r.data.status === "Pending" && tries.current++ < 30) timer = setTimeout(poll, 2000);
      }).catch((e) => setError(errorMessage(e, "Booking not found.")));
    };
    poll();
    return () => clearTimeout(timer);
  }, [tranId]);

  if (error) return <main className="page"><div className="container narrow"><div className="alert alert-error"><Icon.Alert size={18} /> {error}</div></div></main>;

  if (!p || p.status === "Pending") {
    return (
      <main className="page">
        <div className="container narrow card empty">
          <div className="icon"><span className="spinner" /></div>
          <h3>Confirming your payment…</h3>
          <p className="muted" style={{ marginTop: 6 }}>This usually takes a few seconds. Please don't close this page.</p>
          {p && tries.current > 30 && <Link className="btn btn-outline" style={{ marginTop: 20 }} to={`/payment?tran_id=${tranId}`}>Back to payment</Link>}
        </div>
      </main>
    );
  }

  if (p.status !== "Paid") {
    return (
      <main className="page">
        <div className="container narrow card empty">
          <div className="icon"><Icon.Alert size={28} /></div>
          <h3>We couldn't confirm this payment</h3>
          <p className="muted" style={{ marginTop: 6 }}>Status: {p.status}. If money was taken from your account, contact support with reference <b className="mono">{p.tran_id}</b>.</p>
          <Link className="btn btn-primary" style={{ marginTop: 20 }} to="/">Search again</Link>
        </div>
      </main>
    );
  }

  const paid = p.bookings.filter((b) => b.status === "Paid");

  return (
    <main className="page">
      <div className="container narrow stack gap-24">
        <div className="center no-print">
          <div className="success-icon"><Icon.Check size={32} strokeWidth={3} /></div>
          <h1 style={{ fontSize: 30 }}>You're booked!</h1>
          <p className="muted" style={{ marginTop: 8 }}>We've emailed your e-ticket to <b className="bold">{p.customer_email}</b>.</p>
        </div>

        <TicketCard payment={p} bookings={paid} />

        <div className="row gap-12 wrap no-print" style={{ justifyContent: "center" }}>
          <a className="btn btn-dark" href={`${API_URL}/api/payments/${tranId}/ticket.pdf`}><Icon.Download size={18} /> Download PDF</a>
          <button className="btn btn-outline" onClick={() => window.print()}><Icon.Printer size={18} /> Print</button>
          <Link className="btn btn-ghost" to="/">Book another trip</Link>
        </div>
        <p className="tiny muted center">Please arrive at the counter 15 minutes before departure with this e-ticket.</p>
      </div>
    </main>
  );
}
