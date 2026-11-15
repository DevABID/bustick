import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import Icon from "../components/Icons";
import { useToast } from "../components/Toast";
import { money, prettyDate, time12 } from "../format";

const METHODS = {
  sslcommerz: ["bKash", "Nagad", "Rocket", "Visa", "Mastercard", "AMEX", "Net banking"],
  stripe: ["Visa", "Mastercard", "AMEX", "Apple Pay", "Google Pay"],
  demo: ["Demo"],
};
const GATEWAY = { sslcommerz: "SSLCommerz", stripe: "Stripe", demo: "Demo gateway" };

/** Seconds remaining until a deadline set from the server's `seconds_left`. */
function useCountdown(payment) {
  const [deadline, setDeadline] = useState(null);
  const [, tick] = useState(0);
  useEffect(() => {
    if (payment) setDeadline(Date.now() + payment.seconds_left * 1000);
  }, [payment]);
  useEffect(() => {
    const t = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, []);
  if (!payment) return 0;
  const end = deadline ?? Date.now() + payment.seconds_left * 1000;
  return Math.max(0, Math.round((end - Date.now()) / 1000));
}

export default function Payment() {
  const [params] = useSearchParams();
  const tranId = params.get("tran_id");
  const navigate = useNavigate();
  const notify = useToast();
  const [p, setP] = useState(null);
  const [error, setError] = useState("");
  const [paying, setPaying] = useState(false);
  const left = useCountdown(p);

  useEffect(() => {
    if (!tranId) { setError("No booking found."); return; }
    api.get(`/payments/${tranId}/`).then((r) => {
      if (r.data.status === "Paid") navigate(`/confirmation?tran_id=${tranId}`, { replace: true });
      else setP(r.data);
    }).catch((e) => setError(errorMessage(e, "Booking not found.")));
  }, [tranId, navigate]);

  const pay = async () => {
    setPaying(true);
    try {
      const { data } = await api.post(`/payments/${tranId}/checkout/`);
      window.location.assign(data.redirect_url);
    } catch (e) {
      notify(errorMessage(e), "error");
      setPaying(false);
    }
  };

  const cancel = async () => {
    await api.post(`/payments/${tranId}/cancel/`).catch(() => {});
    notify("Your seats have been released.", "success");
    navigate(`/seats/${p.schedule.id}`);
  };

  if (error) return <main className="page"><div className="container narrow"><div className="alert alert-error"><Icon.Alert size={18} /> {error}</div></div></main>;
  if (!p) return <main className="page"><div className="container narrow"><div className="skeleton" style={{ height: 420 }} /></div></main>;

  const s = p.schedule;
  const expired = p.status !== "Pending" || left <= 0;
  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");

  return (
    <main className="page">
      <div className="container narrow stack gap-16">
        <div className="row between wrap gap-12">
          <h1 style={{ fontSize: 28 }}>Review &amp; pay</h1>
          {!expired && <span className={`timer ${left < 120 ? "low" : ""}`} aria-live="polite"><Icon.Timer size={18} /> Seats held for {mm}:{ss}</span>}
        </div>

        {params.get("failed") && <div className="alert alert-error"><Icon.Alert size={18} /> The payment didn't go through. No money was taken. You can try again.</div>}
        {params.get("cancelled") && !expired && <div className="alert alert-warn"><Icon.Alert size={18} /> Payment was cancelled. Your seats are still held, so you can try again.</div>}

        {expired ? (
          <div className="card empty">
            <div className="icon"><Icon.Clock size={28} /></div>
            <h3>Your seat hold has expired</h3>
            <p className="muted" style={{ marginTop: 6 }}>The seats were released so others can book them. Please choose your seats again.</p>
            <Link className="btn btn-primary" style={{ marginTop: 20 }} to={`/seats/${s.id}`}>Choose seats again</Link>
          </div>
        ) : (
          <>
            <div className="card ticket">
              <div className="ticket-head">
                <div className="stack gap-4"><span className="label" style={{ color: "#94a3b8" }}>Trip</span><h2>{s.from_city} → {s.to_city}</h2></div>
                <span className="badge badge-green">{p.bookings.length} seat{p.bookings.length > 1 ? "s" : ""}</span>
              </div>
              <div className="ticket-grid">
                <div className="stack gap-4"><span className="label">Date</span><b className="bold">{prettyDate(s.date)}</b></div>
                <div className="stack gap-4"><span className="label">Departure</span><b className="bold">{time12(s.departure_time)}</b></div>
                <div className="stack gap-4"><span className="label">Bus</span><b className="bold">{s.bus_name}</b></div>
                <div className="stack gap-4"><span className="label">Seats</span><b className="bold">{p.bookings.map((b) => b.seat_number).join(", ")}</b></div>
              </div>
              <div className="ticket-cut" />
              <div className="card-pad stack gap-4">
                <div className="kv"><span className="muted">Passenger</span><span className="bold">{p.customer_name}</span></div>
                <div className="kv"><span className="muted">Ticket sent to</span><span>{p.customer_email}</span></div>
                <div className="kv"><span className="muted">{p.bookings.length} × {money(s.price, p.currency)}</span><span>{money(p.amount, p.currency)}</span></div>
                <div className="kv"><b className="bold">Total to pay</b><b className="price">{money(p.amount, p.currency)}</b></div>
              </div>
            </div>

            <div className="card card-pad stack gap-16">
              <div className="row gap-8"><Icon.Shield size={20} style={{ color: "#16a34a" }} /><b className="bold">{p.provider === "demo" ? "Test checkout" : `Pay securely with ${GATEWAY[p.provider] || "our gateway"}`}</b></div>
              <div className="pay-methods">{p.provider !== "demo" && (METHODS[p.provider] || []).map((m) => <span key={m}>{m}</span>)}</div>
              {p.provider === "demo" && <div className="alert alert-info"><Icon.Alert size={18} /> Demo mode: no real payment is taken. Set PAYMENT_PROVIDER in the server .env to go live.</div>}
              <button className="btn btn-primary btn-lg btn-block" onClick={pay} disabled={paying}>
                {paying ? <span className="spinner" /> : <Icon.Lock size={18} />} Pay {money(p.amount, p.currency)}
              </button>
              <p className="tiny muted center">You'll be taken to the secure payment page. Card details never touch our servers.</p>
              <button className="btn btn-ghost" onClick={cancel}>Cancel and release seats</button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
