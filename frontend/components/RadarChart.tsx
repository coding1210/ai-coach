import type { RadarDomain } from "@/lib/types";

// Hand-rolled SVG radar: one axis per assessed domain, two polygons
// (target = hairline dashed, current = signal-lime). No charting dependency.
export default function RadarChart({ radar }: { radar: RadarDomain[] }) {
  const size = 320;
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 56;
  const maxLevel = 5;
  const n = radar.length;

  if (n < 3) {
    return (
      <p className="text-sm text-dim">
        Radar needs at least three assessed domains.
      </p>
    );
  }

  const angleFor = (i: number) => (Math.PI * 2 * i) / n - Math.PI / 2;
  const point = (i: number, value: number) => {
    const rad = (value / maxLevel) * r;
    const a = angleFor(i);
    return [cx + rad * Math.cos(a), cy + rad * Math.sin(a)] as const;
  };
  const poly = (key: "current" | "target") =>
    radar.map((d, i) => point(i, d[key]).join(",")).join(" ");

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      className="w-full max-w-[360px]"
      role="img"
      aria-label="Radar of current vs target proficiency by domain"
    >
      {/* grid rings */}
      {[1, 2, 3, 4, 5].map((lvl) => (
        <polygon
          key={lvl}
          points={radar.map((_, i) => point(i, lvl).join(",")).join(" ")}
          fill="none"
          stroke="#22262e"
          strokeWidth={1}
        />
      ))}
      {/* spokes + labels */}
      {radar.map((d, i) => {
        const [x, y] = point(i, maxLevel);
        const [lx, ly] = point(i, maxLevel + 0.85);
        return (
          <g key={d.domain_id}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="#22262e" strokeWidth={1} />
            <text
              x={lx}
              y={ly}
              fontSize={8.5}
              letterSpacing={0.6}
              fill="#767d89"
              textAnchor="middle"
              dominantBaseline="middle"
              style={{ fontFamily: "var(--font-geist-mono)", textTransform: "uppercase" }}
            >
              {d.domain_name.replace(/ \(.*\)/, "").slice(0, 16)}
            </text>
          </g>
        );
      })}
      {/* target — hairline dashed */}
      <polygon
        points={poly("target")}
        fill="none"
        stroke="#4a5058"
        strokeWidth={1.25}
        strokeDasharray="3 3"
      />
      {/* current — signal lime; grows in from the centre on reveal */}
      <g className="radar-current">
        <polygon
          points={poly("current")}
          fill="rgba(200,241,105,0.13)"
          stroke="#c8f169"
          strokeWidth={2}
          strokeLinejoin="round"
        />
        {radar.map((d, i) => {
          const [x, y] = point(i, d.current);
          return <circle key={d.domain_id} cx={x} cy={y} r={2.6} fill="#c8f169" />;
        })}
      </g>
    </svg>
  );
}
