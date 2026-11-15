import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import Icon from "../components/Icons";
import SearchForm from "../components/SearchForm";
import { money, prettyDate, seatClassLabel, time12 } from "../format";

const SORTS = [
  { value: "time", label: "Earliest departure" },
  { value: "price", label: "Lowest price" },
  { value: "-price", label: "Highest price" },
];

function TripSkeleton() {
  return (
    <div className="card trip-card" aria-hidden="true">
      <div className="stack gap-8"><div className="skeleton" style={{ height: 20, width: "70%" }} /><div className="skeleton" style={{ height: 16, width: "40%" }} /></div>
      <div className="skeleton" style={{ height: 24 }} />
      <div className="skeleton" style={{ height: 44 }} />
    </div>
  );
}

export default function BusList() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const from = params.get("from") || "";
  const to = params.get("to") || "";
  const date = params.get("date") || "";
  const [sort, setSort] = useState("time");
  const [trips, setTrips] = useState(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [nextDates, setNextDates] = useState([]);

  useEffect(() => {
    setTrips(null); setError(""); setEditing(false);
    api.get("/schedules/", { params: { from, to, date, sort } })
      .then((r) => setTrips(r.data))
      .catch((e) => { setError(errorMessage(e)); setTrips([]); });
  }, [from, to, date, sort]);

  useEffect(() => {
    setNextDates([]);
    if (trips && trips.length === 0 && from && to) {
      api.get("/schedules/next-dates/", { params: { from, to } }).then((r) => setNextDates(r.data)).catch(() => {});
    }
  }, [trips, from, to]);

  const goDate = (d) => navigate(`/buses?${new URLSearchParams({ from, to, date: d })}`);

  return (
    <>
      <div className="summary-bar">
        <div className="container row between wrap gap-16">
          <div className="stack gap-4">
            <h1>{from} <Icon.Arrow size={20} /> {to}</h1>
            <span className="small" style={{ color: "#94a3b8" }}>{prettyDate(date)}{trips ? ` · ${trips.length} bus${trips.length === 1 ? "" : "es"} found` : ""}</span>
          </div>
          <button className="btn btn-outline" onClick={() => setEditing(!editing)}>
            <Icon.Search size={18} /> {editing ? "Close" : "Change search"}
          </button>
        </div>
      </div>

      <main className="page">
        <div className="container stack gap-16">
          {editing && <div className="card card-pad"><SearchForm compact initial={{ from, to, date }} /></div>}

          <div className="row between wrap gap-12">
            <h2 style={{ fontSize: 20 }}>Available buses</h2>
            <label className="row gap-8 small">
              <Icon.Sort size={18} /> <span className="sr-only">Sort by</span>
              <select className="input" style={{ minHeight: 40, width: 210 }} value={sort} onChange={(e) => setSort(e.target.value)}>
                {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </label>
          </div>

          {error && <div className="alert alert-error"><Icon.Alert size={18} /> {error}</div>}

          {trips === null && [0, 1, 2].map((i) => <TripSkeleton key={i} />)}

          {trips && trips.length === 0 && !error && (
            <div className="card empty">
              <div className="icon"><Icon.Calendar size={28} /></div>
              <h3>No buses on {prettyDate(date, { weekday: "long", day: "numeric", month: "long" })}</h3>
              {nextDates.length > 0 ? (
                <>
                  <p className="muted" style={{ marginTop: 6 }}>Good news: there are buses from {from} to {to} on these dates.</p>
                  <div className="date-chips">
                    {nextDates.map((d) => (
                      <button key={d.date} className="date-chip" onClick={() => goDate(d.date)}>
                        <b>{prettyDate(d.date, { weekday: "short", day: "numeric", month: "short" })}</b>
                        <span>{d.trips} bus{d.trips === 1 ? "" : "es"} · from {money(d.min_price)}</span>
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <p className="muted" style={{ marginTop: 6 }}>There are no upcoming trips on this route yet. Try a different route.</p>
                  <button className="btn btn-outline" style={{ marginTop: 20 }} onClick={() => setEditing(true)}>Change search</button>
                </>
              )}
            </div>
          )}

          {trips && trips.map((t) => {
            const soldOut = t.seats_left === 0;
            const few = t.seats_left > 0 && t.seats_left <= 5;
            return (
              <article key={t.id} className="card trip-card">
                <div className="stack gap-8">
                  <h3 style={{ fontSize: 18 }}>{t.bus_name}</h3>
                  <div className="row gap-8 wrap">
                    <span className="badge badge-blue">{t.bus_type === "AC" ? <Icon.Snow size={12} /> : null}{t.bus_type}</span>
                    <span className="badge badge-gray">{seatClassLabel(t.seat_type)}</span>
                  </div>
                </div>
                <div className="trip-time">
                  <div className="stack"><b>{time12(t.departure_time)}</b><span className="tiny muted">{t.from_city}</span></div>
                  <span className="trip-line" />
                  <Icon.Bus size={18} style={{ color: "#94a3b8" }} />
                  <span className="trip-line" />
                  <div className="stack" style={{ textAlign: "right" }}><b style={{ fontSize: 16 }}>{t.to_city}</b><span className="tiny muted">{prettyDate(t.date, { day: "numeric", month: "short" })}</span></div>
                </div>
                <div className="stack gap-8 trip-cta">
                  <span className="price">{money(t.price)}</span>
                  <span className={`small ${few ? "" : "muted"}`} style={few ? { color: "#b45309", fontWeight: 600 } : undefined}>
                    {soldOut ? "Sold out" : few ? `Only ${t.seats_left} seats left` : `${t.seats_left} seats left`}
                  </span>
                  <button className="btn btn-primary" disabled={soldOut} onClick={() => navigate(`/seats/${t.id}`)}>
                    Select seats
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </main>
    </>
  );
}
