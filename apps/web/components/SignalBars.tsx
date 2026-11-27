export interface SignalBarsProps {
  rssi: number | null;
}

export function SignalBars({ rssi }: SignalBarsProps) {
  let filled = 0;
  let label = "Tidak ada sinyal";

  if (rssi !== null) {
    if (rssi > -70) {
      filled = 4;
      label = `Sinyal sangat kuat (${rssi} dBm)`;
    } else if (rssi > -85) {
      filled = 3;
      label = `Sinyal kuat (${rssi} dBm)`;
    } else if (rssi > -100) {
      filled = 2;
      label = `Sinyal sedang (${rssi} dBm)`;
    } else {
      filled = 1;
      label = `Sinyal lemah (${rssi} dBm)`;
    }
  }

  return (
    <div
      className="signal-bars"
      role="img"
      aria-label={label}
      title={label}
    >
      {[1, 2, 3, 4].map((bar) => (
        <span
          key={bar}
          className={`signal-bar ${bar <= filled ? "is-filled" : "is-empty"}`}
          style={{ height: `${bar * 25}%` }}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}
