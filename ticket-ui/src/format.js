const CURRENCY_SYMBOL = { BDT: "৳", USD: "$", EUR: "€", GBP: "£", INR: "₹" };

export function money(amount, currency = "BDT") {
  const sym = CURRENCY_SYMBOL[currency] || `${currency} `;
  return `${sym}${Number(amount || 0).toLocaleString("en-US")}`;
}

/** "07:30:00" -> "7:30 AM" */
export function time12(t) {
  if (!t) return "";
  const [h, m] = t.split(":").map(Number);
  const suffix = h >= 12 ? "PM" : "AM";
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${suffix}`;
}

/** "2026-11-20" -> "Fri, 20 Nov 2026" (no timezone shift) */
export function prettyDate(d, opts = { weekday: "short", day: "numeric", month: "short", year: "numeric" }) {
  if (!d) return "";
  const [y, m, day] = d.split("-").map(Number);
  return new Date(y, m - 1, day).toLocaleDateString("en-GB", opts);
}

export function todayISO(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function seatClassLabel(seatType) {
  return seatType === "BUSINESS" ? "Business" : "Economy";
}
