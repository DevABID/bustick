import React, { useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import Icon from "../components/Icons";

const FAQ = [
  ["How do I get my ticket?", "After payment your e-ticket appears on screen and a PDF copy is emailed to you. You can also find it any time on the Find my ticket page with your PNR and email."],
  ["How long are my seats held?", "Selected seats are held for 10 minutes while you pay. If payment isn't completed in time, the seats are released for other passengers."],
  ["Which payment methods can I use?", "bKash, Nagad, Rocket, Visa, Mastercard, AMEX and internet banking, through our secure payment gateway. We never see or store your card details."],
  ["What if my payment fails?", "No money is taken for a failed payment. Your seats stay held until the timer runs out, so you can try again."],
  ["Money was taken but I didn't get a ticket", "This is rare and is usually fixed automatically within a few minutes. If not, send us a message below with the time of payment and we'll sort it out."],
  ["Can I book for more than one person?", "Yes. You can select up to 4 seats in a single booking. Each seat gets its own PNR."],
];

const TOPICS = [
  ["booking", "Booking problem"],
  ["payment", "Payment or refund"],
  ["return", "Ticket return"],
  ["other", "Something else"],
];

const EMPTY = { name: "", email: "", phone: "", topic: "booking", pnr: "", message: "", website: "" };

function ContactForm() {
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [state, setState] = useState({ busy: false, done: "", error: "" });

  const set = (k) => (e) => { setForm({ ...form, [k]: e.target.value }); if (errors[k]) setErrors({ ...errors, [k]: undefined }); };

  const validate = () => {
    const e = {};
    if (form.name.trim().length < 2) e.name = "Please enter your name.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) e.email = "Enter a valid email so we can reply.";
    if (form.message.trim().length < 10) e.message = "Please tell us a little more (at least 10 characters).";
    setErrors(e);
    return !Object.keys(e).length;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    if (!validate()) return;
    setState({ busy: true, done: "", error: "" });
    try {
      const { data } = await api.post("/support/", { ...form, pnr: form.pnr.trim().toUpperCase() });
      setState({ busy: false, done: data.message, error: "" });
      setForm(EMPTY);
    } catch (e) {
      const fieldErrs = e.response?.status === 400 ? e.response.data : null;
      if (fieldErrs && typeof fieldErrs === "object") {
        setErrors(Object.fromEntries(Object.entries(fieldErrs).map(([k, v]) => [k, Array.isArray(v) ? v[0] : String(v)])));
      }
      setState({ busy: false, done: "", error: e.response?.status === 429 ? "You've sent several messages already. Please wait a while before sending another." : errorMessage(e) });
    }
  };

  if (state.done) {
    return (
      <div className="card empty" role="status">
        <div className="success-icon"><Icon.Check size={30} strokeWidth={3} /></div>
        <h3>Message sent</h3>
        <p className="muted" style={{ marginTop: 6 }}>{state.done}</p>
        <button className="btn btn-outline" style={{ marginTop: 20 }} onClick={() => setState({ busy: false, done: "", error: "" })}>Send another message</button>
      </div>
    );
  }

  const field = (k, label, props = {}, IconCmp = null) => (
    <div className="field">
      <label htmlFor={`s-${k}`}>{label}</label>
      <div className={IconCmp ? "input-wrap" : undefined}>
        {IconCmp && <IconCmp size={18} />}
        <input id={`s-${k}`} className={`input ${errors[k] ? "invalid" : ""}`} value={form[k]} onChange={set(k)}
          aria-invalid={!!errors[k]} aria-describedby={errors[k] ? `s-${k}-err` : undefined} {...props} />
      </div>
      {errors[k] && <span id={`s-${k}-err`} className="field-error">{errors[k]}</span>}
    </div>
  );

  return (
    <form className="card card-pad stack gap-16" onSubmit={submit} noValidate>
      <div className="stack gap-4">
        <h2 style={{ fontSize: 22 }}>Send us a message</h2>
        <p className="muted small">We usually reply within 24 hours.</p>
      </div>
      <div className="grid-2" style={{ gap: 16 }}>
        {field("name", "Your name", { autoComplete: "name", placeholder: "Rahim Uddin" }, Icon.User)}
        {field("email", "Email", { type: "email", autoComplete: "email", placeholder: "you@example.com" }, Icon.Mail)}
        {field("phone", "Mobile (optional)", { type: "tel", autoComplete: "tel", placeholder: "01712345678" }, Icon.Phone)}
        {field("pnr", "PNR (if you have one)", { placeholder: "e.g. BR7K9X22", maxLength: 10 }, Icon.Ticket)}
      </div>
      <div className="field">
        <label htmlFor="s-topic">What do you need help with?</label>
        <select id="s-topic" className="input" value={form.topic} onChange={set("topic")}>
          {TOPICS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor="s-message">Message</label>
        <textarea id="s-message" className={`input textarea ${errors.message ? "invalid" : ""}`} rows={5} maxLength={3000}
          placeholder="Tell us what happened, including the travel date and route if relevant." value={form.message} onChange={set("message")}
          aria-invalid={!!errors.message} aria-describedby={errors.message ? "s-message-err" : undefined} />
        {errors.message && <span id="s-message-err" className="field-error">{errors.message}</span>}
      </div>
      {/* Honeypot: hidden from people, filled in by spam bots */}
      <input type="text" name="website" value={form.website} onChange={set("website")} tabIndex={-1} autoComplete="off" className="sr-only" aria-hidden="true" />
      {state.error && <div className="alert alert-error" role="alert"><Icon.Alert size={18} /> {state.error}</div>}
      <button className="btn btn-primary btn-lg" disabled={state.busy}>
        {state.busy ? <span className="spinner" /> : <Icon.Mail size={18} />} Send message
      </button>
    </form>
  );
}

export default function Support() {
  return (
    <main className="page">
      <div className="container stack gap-24" style={{ maxWidth: 1000 }}>
        <div className="stack gap-8">
          <span className="label">Help centre</span>
          <h1 style={{ fontSize: 34 }}>How can we help?</h1>
          <p className="muted">Find quick answers below, or send us a message and our team will get back to you.</p>
        </div>

        <div className="grid-3">
          <Link to="/check-ticket" className="card feature help-tile"><div className="icon"><Icon.Ticket size={24} /></div><h3>Find my ticket</h3><p className="muted small">View or download your e-ticket</p></Link>
          <Link to="/return-ticket" className="card feature help-tile"><div className="icon"><Icon.Return size={24} /></div><h3>Return a ticket</h3><p className="muted small">Cancel and get a refund</p></Link>
          <a href="#contact" className="card feature help-tile"><div className="icon"><Icon.Mail size={24} /></div><h3>Contact support</h3><p className="muted small">Send us a message</p></a>
        </div>

        <div className="support-layout">
          <div className="card card-pad faq">
            <h2 style={{ fontSize: 22, marginBottom: 4 }}>Frequently asked questions</h2>
            {FAQ.map(([q, a]) => (
              <details key={q}><summary>{q} <Icon.Arrow size={16} style={{ transform: "rotate(90deg)", flexShrink: 0 }} /></summary><p className="muted">{a}</p></details>
            ))}
            <details id="policy" open={window.location.hash === "#policy"}>
              <summary>Cancellation &amp; refund policy <Icon.Arrow size={16} style={{ transform: "rotate(90deg)", flexShrink: 0 }} /></summary>
              <p className="muted">Tickets can be returned online up to 12 hours before departure. The fare is refunded to your original payment method, usually within 5–7 working days. Returns are not possible within 12 hours of departure.</p>
            </details>
          </div>
          <div id="contact"><ContactForm /></div>
        </div>
      </div>
    </main>
  );
}
