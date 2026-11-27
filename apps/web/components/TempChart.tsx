"use client";

import {
  CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

type Point = { x: number; temp_c: number | null };

export function TempChart({
  points, min, max, xLabel, formatX, height = 280, domainX,
}: {
  points: Point[]; min: number | null; max: number | null; xLabel: string;
  formatX: (x: number) => string; height?: number; domainX?: [number, number];
}) {
  const temps = points.flatMap((p) => (p.temp_c == null ? [] : [p.temp_c]));
  const low = Math.floor(Math.min(...temps, min ?? 0, 0) - 1);
  const high = Math.ceil(Math.max(...temps, max ?? 4, 4) + 1);
  return (
    <div className="chart" role="img" aria-label={`Grafik suhu terhadap ${xLabel}`}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={points} margin={{ top: 8, right: 16, bottom: 4, left: -8 }}>
          <CartesianGrid stroke="var(--color-border)" vertical={false} />
          {min != null && max != null && (
            <ReferenceArea y1={min} y2={max} fill="var(--color-safe-bg)" fillOpacity={1} ifOverflow="hidden" />
          )}
          <XAxis dataKey="x" type="number" domain={domainX ?? ["dataMin", "dataMax"]} tickFormatter={formatX}
            stroke="var(--color-text-secondary)" fontSize={12} tickMargin={6} />
          <YAxis domain={[low, high]} stroke="var(--color-text-secondary)" fontSize={12} unit=" °C" width={64} />
          {max != null && <ReferenceLine y={max} stroke="var(--color-critical)" strokeDasharray="6 4"
            label={{ value: `Batas atas ${max} °C`, position: "insideTopRight", fill: "var(--color-critical-fg)", fontSize: 12, fontWeight: 600 }} />}
          {min != null && <ReferenceLine y={min} stroke="var(--color-info)" strokeDasharray="6 4"
            label={{ value: `Batas bawah ${min} °C`, position: "insideBottomRight", fill: "var(--color-info-fg)", fontSize: 12, fontWeight: 600 }} />}
          <Tooltip formatter={(v) => [`${Number(v).toFixed(2)} °C`, "Suhu"]} labelFormatter={(x) => formatX(Number(x))}
            contentStyle={{ borderRadius: 10, border: "1px solid var(--color-border)", fontWeight: 600 }} />
          <Line type="monotone" dataKey="temp_c" stroke="var(--color-primary)" strokeWidth={2.5}
            dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
