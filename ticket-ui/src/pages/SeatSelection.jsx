import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import Icon from "../components/Icons";
import { useToast } from "../components/Toast";
import { money, prettyDate, seatClassLabel, time12 } from "../format";

const MAX_SEATS = 4;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+?\d{10,15}$/;

export default function SeatSelection() {
  const { id } = useParams();
  const navigate = useNavigate();
  const notify = useToast();
  const [trip, setTrip] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [selected, setSelected] = useState([]);
  const [form, setForm] = useState({ customer_name: "", customer_email: "", phone: "" });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(() => {
    return api.get(`/schedules/${id}/`).then((r) => { setTrip(r.data); return r.data; })
      .catch((e) => setLoadError(errorMessage(e, "This trip could not be found.")));
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const toggle = (seat) => {
    setSelected((cur) => {
      if (cur.includes(seat)) return cur.filter((s) => s !== seat);
      if (cur.length >= MAX_SEATS) { notify(`You can book up to ${MAX_SEATS} seats at a time.`, "error"); return cur; }
      return [...cur, seat];
    });
  };

  const validate = () => {
    const e = {};
    if (form.customer_name.trim().length < 2) e.customer_name = "Enter the passenger's full name.";
    if (!EMAIL_RE.test(form.customer_email.trim())) e.customer_email = "Enter a valid email. Your ticket is sent here.";
    if (!PHONE_RE.test(form.phone.replace(/[\s-]/g, ""))) e.phone = "Enter a valid mobile number, e.g. 01712345678.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    if (!selected.length) return notify("Select at least one seat on the map.", "error");
    if (!validate()) return;
    setSubmitting(true);
    try {
      const { data } = await api.post("/bookings/", {
        schedule: Number(id), seats: selected,
        customer_name: form.customer_name.trim(), customer_email: form.customer_email.trim(),
        phone: form.phone.replace(/[\s-]/g, ""),
      });
      navigate(`/payment?tran_id=${data.tran_id}`);
    } catch (e) {
      notify(errorMessage(e), "error");
      if (e.response?.status === 409) {
        const fresh = await load();
        if (fresh) setSelected((cur) => cur.filter((s) => !fresh.booked_seats.includes(s)));
      }
      setSubmitting(false);
    }
  };

  if (loadError) return <main className="page"><div className="container narrow"><div className="alert alert-error"><Icon.Alert size={18} /> {loadError}</div></div></main>;
  if (!trip) return <main className="page"><div className="container"><div className="skeleton" style={{ height: 480 }} /></div></main>;

  const cols = trip.seat_type === "BUSINESS" ? 4 : 5;
  const total = selected.length * trip.price;
  const set = (k) => (e) => { setForm({ ...form, [k]: e.target.value }); if (errors[k]) setErrors({ ...errors, [k]: undefined }); };

  return (
    <main className="page">
      <div className="container stack gap-24">
        <div className="stack gap-8">
          <Link to={`/buses?${new URLSearchParams({ from: trip.from_city, to: trip.to_city, date: trip.date })}`} className="small row gap-4">
            <Icon.Arrow size={16} style={{ transform: "rotate(180deg)" }} /> Back to results
          </Link>
          <h1 style={{ fontSize: 28 }}>{trip.bus_name}</h1>
          <div className="row gap-16 wrap muted small">
            <span className="row gap-4"><Icon.MapPin size={16} /> {trip.from_city} → {trip.to_city}</span>
            <span className="row gap-4"><Icon.Calendar size={16} /> {prettyDate(trip.date)}</span>
            <span className="row gap-4"><Icon.Clock size={16} /> {time12(trip.departure_time)}</span>
            <span className="badge badge-blue">{trip.bus_type}</span>
            <span className="badge badge-gray">{seatClassLabel(trip.seat_type)}</span>
          </div>
        </div>

        <div className="seat-layout">
          <div className="card card-pad stack gap-24">
            <div className="row between wrap gap-12">
              <h2 style={{ fontSize: 20 }}>Choose your seats</h2>
              <div className="legend">
                <span><i /> Available</span><span><i className="sel" /> Selected</span><span><i className="taken" /> Booked</span>
              </div>
            </div>
            <div className="bus-shell" role="group" aria-label="Seat map">
              <div className="bus-front"><span className="wheel" title="Driver"><Icon.Wheel size={22} /></span></div>
              <div className="seat-grid" style={{ gridTemplateColumns: `repeat(${cols}, auto)` }}>
                {trip.layout.map((seat, i) => {
                  if (!seat) return <span key={`aisle-${i}`} className="aisle" />;
                  const taken = trip.booked_seats.includes(seat);
                  const isSel = selected.includes(seat);
                  return (
                    <button key={seat} type="button" className={`seat ${isSel ? "selected" : ""}`} disabled={taken}
                      aria-pressed={isSel} aria-label={`Seat ${seat}${taken ? ", booked" : isSel ? ", selected" : ""}`}
                      onClick={() => toggle(seat)}>
                      {seat}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <form className="card card-pad stack gap-16 sticky" onSubmit={submit} noValidate>
            <h2 style={{ fontSize: 20 }}>Booking summary</h2>
            <div>
              <div className="kv"><span className="muted">Seats</span>
                <span className="row gap-4 wrap" style={{ justifyContent: "flex-end" }}>
                  {selected.length ? selected.map((s) => <span key={s} className="chip">{s}</span>) : <span className="muted">None selected</span>}
                </span>
              </div>
              <div className="kv"><span className="muted">Fare per seat</span><span>{money(trip.price)}</span></div>
              <div className="kv"><b className="bold">Total</b><b className="price" style={{ fontSize: 22 }}>{money(total)}</b></div>
            </div>

            <h3 style={{ fontSize: 16 }}>Passenger details</h3>
            {[
              ["customer_name", "Full name", "text", "Rahim Uddin", Icon.User, "name"],
              ["customer_email", "Email", "email", "you@example.com", Icon.Mail, "email"],
              ["phone", "Mobile number", "tel", "01712345678", Icon.Phone, "tel"],
            ].map(([k, label, type, ph, I, ac]) => (
              <div className="field" key={k}>
                <label htmlFor={k}>{label}</label>
                <div className="input-wrap">
                  <I size={18} />
                  <input id={k} type={type} autoComplete={ac} placeholder={ph} className={`input ${errors[k] ? "invalid" : ""}`}
                    value={form[k]} onChange={set(k)} aria-invalid={!!errors[k]} aria-describedby={errors[k] ? `${k}-err` : undefined} />
                </div>
                {errors[k] && <span id={`${k}-err`} className="field-error">{errors[k]}</span>}
              </div>
            ))}

            <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={submitting || !selected.length}>
              {submitting ? <span className="spinner" /> : <Icon.Lock size={18} />}
              {selected.length ? `Continue to payment · ${money(total)}` : "Select a seat to continue"}
            </button>
            <p className="tiny muted center">Seats are held for 10 minutes while you pay.</p>
          </form>
        </div>
      </div>
    </main>
  );
}
