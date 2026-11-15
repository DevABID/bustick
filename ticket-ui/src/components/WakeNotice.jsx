import React, { useEffect, useState } from "react";
import { onSlowServer } from "../api";

export default function WakeNotice() {
  const [slow, setSlow] = useState(false);
  useEffect(() => onSlowServer(setSlow), []);
  if (!slow) return null;
  return (
    <div className="wake-notice" role="status" aria-live="polite">
      <span className="spinner" /> Connecting to the server… this can take up to a minute the first time.
    </div>
  );
}
