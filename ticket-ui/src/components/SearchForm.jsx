import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { todayISO } from "../format";
import Icon from "./Icons";

export default function SearchForm({ initial = {}, compact = false }) {
  const navigate = useNavigate();
  const [routes, setRoutes] = useState([]);
  const [from, setFrom] = useState(initial.from || "");
  const [to, setTo] = useState(initial.to || "");
  const [date, setDate] = useState(initial.date || todayISO(1));
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/routes/").then((r) => setRoutes(r.data)).catch(() => setError("Couldn't load routes. Is the server running?"));
  }, []);

  const fromCities = useMemo(() => [...new Set(routes.map((r) => r.from_city))].sort(), [routes]);
  const toCities = useMemo(
    () => [...new Set(routes.filter((r) => !from || r.from_city === from).map((r) => r.to_city))].sort(),
    [routes, from]
  );

  useEffect(() => {
    if (to && routes.length && !toCities.includes(to)) setTo("");
  }, [to, toCities, routes.length]);

  const swap = () => { setFrom(to); setTo(from); };

  const submit = (e) => {
    e.preventDefault();
    if (!from || !to) return setError("Choose where you're leaving from and going to.");
    if (!date) return setError("Pick a travel date.");
    setError("");
    navigate(`/buses?${new URLSearchParams({ from, to, date })}`);
  };

  return (
    <form onSubmit={submit} className={compact ? "" : "card search-card"} noValidate>
      <div className="search-grid">
        <div className="field">
          <label htmlFor="from">From</label>
          <div className="input-wrap">
            <Icon.MapPin size={18} />
            <select id="from" className="input" value={from} onChange={(e) => setFrom(e.target.value)}>
              <option value="">Leaving from</option>
              {fromCities.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <button type="button" className="swap-btn" onClick={swap} aria-label="Swap from and to"><Icon.Swap size={18} /></button>
        <div className="field">
          <label htmlFor="to">To</label>
          <div className="input-wrap">
            <Icon.MapPin size={18} />
            <select id="to" className="input" value={to} onChange={(e) => setTo(e.target.value)}>
              <option value="">Going to</option>
              {toCities.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <div className="field">
          <label htmlFor="date">Travel date</label>
          <div className="input-wrap">
            <Icon.Calendar size={18} />
            <input id="date" type="date" className="input" min={todayISO()} value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
        </div>
        <button type="submit" className="btn btn-primary btn-lg"><Icon.Search size={18} /> Search buses</button>
      </div>
      {error && <p className="field-error" style={{ marginTop: 12 }} role="alert">{error}</p>}
    </form>
  );
}
