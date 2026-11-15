import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api";
import Icon from "../components/Icons";
import SearchForm from "../components/SearchForm";
import { money, prettyDate, todayISO } from "../format";

const PAY_METHODS = ["bKash", "Nagad", "Rocket", "VISA", "Mastercard", "AMEX", "Net banking"];

const FEATURES = [
  { icon: Icon.Seat, title: "Choose your exact seat", text: "A live seat map shows which seats are free, so you can pick window, aisle or seats together." },
  { icon: Icon.Shield, title: "Safe, verified payments", text: "Pay with bKash, Nagad, Rocket or card on a secure gateway. Your seats are held while you pay." },
  { icon: Icon.Mail, title: "E-ticket in seconds", text: "Your ticket and PNR appear right away, with a PDF copy sent to your email." },
  { icon: Icon.Return, title: "Easy online returns", text: "Plans changed? Return your ticket online up to 12 hours before departure." },
];

const STEPS = [
  { icon: Icon.Search, title: "Search", text: "Pick your route and travel date." },
  { icon: Icon.Seat, title: "Choose seats", text: "Compare buses and select seats on the map." },
  { icon: Icon.Card, title: "Pay securely", text: "bKash, Nagad, Rocket or card." },
  { icon: Icon.Ticket, title: "Travel", text: "Show your e-ticket at the counter." },
];

const FAQ = [
  ["How do I get my ticket?", "Right after payment your e-ticket appears on screen and a PDF is emailed to you. You can also find it any time with your PNR and email."],
  ["Is my payment safe?", "Yes. Payments go through a licensed, encrypted payment gateway. We never see or store your card or wallet PIN."],
  ["Can I return my ticket?", "Yes, online, up to 12 hours before departure. The fare is refunded to your original payment method."],
];

function HeroVisual() {
  const seats = ["A1", null, "A2", "A3", "B1", null, "B2", "B3", "C1", null, "C2", "C3", "D1", null, "D2", "D3"];
  const taken = ["A1", "A3", "B2", "C1", "D3"];
  const picked = ["C2", "C3"];
  return (
    <div className="hero-visual" aria-hidden="true">
      <div className="hv-seats card">
        <div className="row between"><b className="bold small">Choose seats</b><span className="hv-wheel"><Icon.Wheel size={16} /></span></div>
        <div className="hv-grid">
          {seats.map((s, i) => s ? (
            <span key={s} className={`hv-seat ${taken.includes(s) ? "taken" : ""} ${picked.includes(s) ? "picked" : ""}`}>{s}</span>
          ) : <span key={i} />)}
        </div>
      </div>
      <div className="hv-ticket card">
        <div className="hv-ticket-head">
          <span className="row gap-8"><span className="logo-mark" style={{ width: 26, height: 26, borderRadius: 7 }}><Icon.Bus size={14} /></span><b>E-ticket</b></span>
          <span className="badge badge-green"><Icon.Check size={12} /> Paid</span>
        </div>
        <div className="row between" style={{ padding: "16px 18px 6px" }}>
          <div className="stack"><span className="label">From</span><b className="hv-city">Dhaka</b></div>
          <Icon.Arrow size={18} style={{ color: "#94a3b8" }} />
          <div className="stack" style={{ textAlign: "right" }}><span className="label">To</span><b className="hv-city">Sylhet</b></div>
        </div>
        <div className="row between small" style={{ padding: "6px 18px 16px" }}>
          <span className="muted">Seats <b className="bold">C2, C3</b></span>
          <span className="muted">PNR <b className="bold mono">K7Q2M9XD</b></span>
        </div>
      </div>
      <div className="hv-toast"><Icon.CheckCircle size={18} /> Ticket sent to your email</div>
    </div>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const [routes, setRoutes] = useState(null);

  useEffect(() => {
    api.get("/routes/").then((r) => setRoutes(r.data.filter((x) => x.next_date).slice(0, 8))).catch(() => setRoutes([]));
  }, []);

  const go = (r) => navigate(`/buses?${new URLSearchParams({
    from: r.from_city, to: r.to_city, date: r.next_date && r.next_date > todayISO() ? r.next_date : todayISO(),
  })}`);

  return (
    <>
      <section className="hero">
        <div className="container hero-layout">
          <div className="hero-copy">
            <span className="hero-eyebrow"><Icon.Bus size={16} /> Intercity bus tickets</span>
            <h1>Your next trip starts <span>with the right seat.</span></h1>
            <p>Compare buses across Bangladesh, choose your seat on a live map and pay in seconds with bKash, Nagad or card.</p>
            <div className="hero-points">
              <span><Icon.CheckCircle size={18} /> Live seat availability</span>
              <span><Icon.CheckCircle size={18} /> Instant e-ticket</span>
              <span><Icon.CheckCircle size={18} /> Online returns</span>
            </div>
          </div>
          <HeroVisual />
        </div>
      </section>

      <div className="container">
        <SearchForm />

        <div className="pay-strip">
          <span className="label">Pay with</span>
          {PAY_METHODS.map((m) => <span key={m} className="pay-logo">{m}</span>)}
        </div>

        <section className="section">
          <div className="section-head">
            <div className="stack gap-4">
              <span className="label">Popular routes</span>
              <h2>Where are you headed?</h2>
            </div>
            <p className="muted small">Lowest fares on upcoming trips</p>
          </div>
          {routes === null ? (
            <div className="grid-4">{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 132 }} />)}</div>
          ) : routes.length === 0 ? (
            <div className="card empty"><p className="muted">New trips are being added. Search above for your route.</p></div>
          ) : (
            <div className="grid-4">
              {routes.map((r) => (
                <button key={r.id} className="card route-card" onClick={() => go(r)}>
                  <span className="route-icon"><Icon.MapPin size={18} /></span>
                  <span className="cities">{r.from_city} <Icon.Arrow size={16} /> {r.to_city}</span>
                  <span className="row between" style={{ width: "100%" }}>
                    <span className="small muted">From <b className="route-price">{money(r.min_price)}</b></span>
                    <span className="tiny muted">{r.trips} trip{r.trips === 1 ? "" : "s"}</span>
                  </span>
                  <span className="tiny muted">Next: {prettyDate(r.next_date, { weekday: "short", day: "numeric", month: "short" })}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="section">
          <div className="section-head">
            <div className="stack gap-4">
              <span className="label">Why BusTick</span>
              <h2>Travel without the counter queue</h2>
            </div>
          </div>
          <div className="grid-4">
            {FEATURES.map(({ icon: I, title, text }) => (
              <div key={title} className="card feature">
                <div className="icon"><I size={24} /></div>
                <h3>{title}</h3>
                <p className="muted small">{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="section">
          <div className="steps-band">
            <div className="stack gap-4" style={{ marginBottom: 28 }}>
              <span className="label" style={{ color: "#86efac" }}>How it works</span>
              <h2 style={{ color: "#fff" }}>Booked in four simple steps</h2>
            </div>
            <ol className="steps">
              {STEPS.map(({ icon: I, title, text }, i) => (
                <li key={title}>
                  <span className="step-icon"><I size={22} /><span className="step-n">{i + 1}</span></span>
                  <b>{title}</b>
                  <span>{text}</span>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="section">
          <div className="grid-2">
            <div className="card card-pad stack gap-16">
              <span className="label">Already booked?</span>
              <h2 style={{ fontSize: 24 }}>Manage your trip</h2>
              <p className="muted">Download your e-ticket again or return a ticket if your plans change.</p>
              <div className="row gap-12 wrap">
                <Link to="/check-ticket" className="btn btn-dark"><Icon.Ticket size={18} /> Find my ticket</Link>
                <Link to="/return-ticket" className="btn btn-outline"><Icon.Return size={18} /> Return a ticket</Link>
              </div>
            </div>
            <div className="card card-pad stack gap-8 faq">
              <span className="label">Questions</span>
              {FAQ.map(([q, a]) => (
                <details key={q}><summary>{q} <Icon.Arrow size={16} style={{ transform: "rotate(90deg)", flexShrink: 0 }} /></summary><p className="muted small">{a}</p></details>
              ))}
              <Link to="/support" className="small" style={{ marginTop: 8 }}>More help &amp; contact us →</Link>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
