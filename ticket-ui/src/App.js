import React, { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import Footer from "./components/Footer";
import Navbar from "./components/Navbar";
import { ToastProvider } from "./components/Toast";
import WakeNotice from "./components/WakeNotice";
import BusList from "./pages/BusList";
import CheckTicket from "./pages/CheckTicket";
import Confirmation from "./pages/Confirmation";
import Home from "./pages/Home";
import NotFound from "./pages/NotFound";
import Payment from "./pages/Payment";
import ReturnTicket from "./pages/ReturnTicket";
import SeatSelection from "./pages/SeatSelection";
import Support from "./pages/Support";

const TITLES = {
  "/": "Book bus tickets online",
  "/buses": "Available buses",
  "/payment": "Review & pay",
  "/confirmation": "Booking confirmed",
  "/check-ticket": "Find my ticket",
  "/return-ticket": "Return a ticket",
  "/support": "Help centre",
};

function ScrollAndTitle() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    const target = hash && document.querySelector(hash);
    if (target) target.scrollIntoView({ behavior: "smooth" });
    else window.scrollTo(0, 0);
    const key = pathname.startsWith("/seats") ? null : pathname;
    document.title = `${TITLES[key] || (pathname.startsWith("/seats") ? "Choose seats" : "BusTick")} · BusTick`;
  }, [pathname, hash]);
  return null;
}

export default function App() {
  return (
    <ToastProvider>
      <ScrollAndTitle />
      <Navbar />
      <WakeNotice />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/buses" element={<BusList />} />
        <Route path="/seats/:id" element={<SeatSelection />} />
        <Route path="/payment" element={<Payment />} />
        <Route path="/confirmation" element={<Confirmation />} />
        <Route path="/check-ticket" element={<CheckTicket />} />
        <Route path="/return-ticket" element={<ReturnTicket />} />
        <Route path="/support" element={<Support />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
      <Footer />
    </ToastProvider>
  );
}
