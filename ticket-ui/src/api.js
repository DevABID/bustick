import axios from "axios";

// Where the Django API lives.
// 1. REACT_APP_API_URL (from .env, .env.production or the host's settings) wins.
// 2. Otherwise: local Django when the site runs on this computer, the live API everywhere else.
const PRODUCTION_API = "https://bustick-api.onrender.com";
const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
export const API_URL = (process.env.REACT_APP_API_URL || (isLocal ? "http://127.0.0.1:8000" : PRODUCTION_API)).replace(/\/$/, "");

// Long timeout: a free Render server can take up to a minute to wake from sleep.
const api = axios.create({ baseURL: `${API_URL}/api`, timeout: 90000 });

/** Turn any API error into one readable sentence. */
export function errorMessage(err, fallback = "Something went wrong. Please try again.") {
  const data = err?.response?.data;
  if (!data) return err?.code === "ECONNABORTED" || !err?.response ? "Can't reach the server. Check your connection." : fallback;
  if (typeof data === "string") return fallback;
  if (data.error) return data.error;
  if (data.detail) return data.detail;
  const first = Object.values(data)[0];
  if (Array.isArray(first)) return String(first[0]);
  if (typeof first === "string") return first;
  return fallback;
}

export default api;

// ---- "Server is waking up" notice for slow first requests ----
let pending = 0;
let timer = null;
const listeners = new Set();
const emit = (slow) => listeners.forEach((fn) => fn(slow));

export function onSlowServer(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function start(config) {
  pending += 1;
  if (!timer) timer = setTimeout(() => emit(true), 4000);
  return config;
}
function finish() {
  pending = Math.max(0, pending - 1);
  if (pending === 0) { clearTimeout(timer); timer = null; emit(false); }
}

api.interceptors.request.use(start);
api.interceptors.response.use((r) => { finish(); return r; }, (e) => { finish(); return Promise.reject(e); });
