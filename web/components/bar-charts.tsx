"use client";

import Link from "next/link";
import { useId, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export type Datum = { label: string; value: number };
export type TagTile = { tag: string; value: number; photo?: string; href: string };

/** Chart/table switch: every chart ships a table view so values never depend on reading the shape. */
function ViewToggle({ table, onChange }: { table: boolean; onChange: (table: boolean) => void }) {
  return (
    <div className="inline-flex rounded-full bg-muted p-0.5 text-xs font-medium">
      {(["Chart", "Table"] as const).map((v) => {
        const active = (v === "Table") === table;
        return (
          <button
            key={v}
            type="button"
            onClick={() => onChange(v === "Table")}
            className={cn(
              "rounded-full px-2.5 py-1 transition-colors",
              active ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {v}
          </button>
        );
      })}
    </div>
  );
}

function DataTable({ data, unit, labelHeader }: { data: Datum[]; unit: string; labelHeader: string }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left">
          <th className="type-eyebrow py-2 font-semibold text-muted-foreground">{labelHeader}</th>
          <th className="type-eyebrow py-2 text-right font-semibold text-muted-foreground">{unit}</th>
        </tr>
      </thead>
      <tbody className="divide-y">
        {data.map((d) => (
          <tr key={d.label}>
            <td className="py-1.5">{d.label}</td>
            <td className="py-1.5 text-right tabular-nums">{d.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Tile placement for up to 8 tags on a 4×3 grid: the most common tag gets the big tile.
const TILE_SPAN = [
  "col-span-2 row-span-2",
  "col-span-2",
  "",
  "",
  "",
  "",
  "",
  "",
];

/**
 * The most common AI tags as a mosaic of real example photos, each labelled with its count.
 * Tiles link to the library filtered by that tag.
 */
export function TagMosaic({ tiles, total }: { tiles: TagTile[]; total: number }) {
  return (
    <div className="grid h-[22rem] grid-cols-4 grid-rows-3 gap-2">
      {tiles.slice(0, 8).map((t, i) => (
        <Link
          key={t.tag}
          href={t.href}
          className={cn("group relative overflow-hidden rounded-xl bg-muted", TILE_SPAN[i])}
          title={`${t.tag}: ${t.value} of ${total} photos`}
        >
          {t.photo ? (
            <img
              src={t.photo}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            />
          ) : null}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 p-2.5 text-white">
            <p className={cn("font-bold capitalize leading-tight", i === 0 ? "text-lg" : "truncate text-[13px]")}>{t.tag}</p>
            <p className={cn("tabular-nums text-white/80", i === 0 ? "text-sm" : "text-[11px]")}>
              {t.value} photos{i === 0 ? ` · ${Math.round((t.value / total) * 100)}% of all` : ""}
            </p>
          </div>
        </Link>
      ))}
    </div>
  );
}

// Monotone cubic interpolation keeps the curve smooth without overshooting between months.
function smoothPath(points: { x: number; y: number }[]): string {
  if (points.length < 2) return points.length ? `M${points[0].x},${points[0].y}` : "";
  const n = points.length;
  const dx = points.slice(1).map((p, i) => p.x - points[i].x);
  const slope = points.slice(1).map((p, i) => (p.y - points[i].y) / dx[i]);
  const tangent = points.map((_, i) => {
    if (i === 0) return slope[0];
    if (i === n - 1) return slope[n - 2];
    return slope[i - 1] * slope[i] <= 0 ? 0 : (slope[i - 1] + slope[i]) / 2;
  });
  let d = `M${points[0].x},${points[0].y}`;
  for (let i = 0; i < n - 1; i++) {
    const h = dx[i] / 3;
    d += ` C${points[i].x + h},${points[i].y + tangent[i] * h} ${points[i + 1].x - h},${points[i + 1].y - tangent[i + 1] * h} ${points[i + 1].x},${points[i + 1].y}`;
  }
  return d;
}

/** Smooth area chart over time (single series) with a hover crosshair + tooltip and a table view. */
export function AreaChart({ data, unit, labelHeader }: { data: Datum[]; unit: string; labelHeader: string }) {
  const [table, setTable] = useState(false);
  const [hover, setHover] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const gradientId = useId();

  const W = 600;
  const H = 220;
  const pad = { top: 28, right: 12, bottom: 28, left: 28 };
  const max = Math.max(1, ...data.map((d) => d.value));
  const niceMax = Math.ceil(max / 5) * 5 || 5;
  const x = (i: number) => pad.left + (i * (W - pad.left - pad.right)) / Math.max(1, data.length - 1);
  const y = (v: number) => pad.top + (1 - v / niceMax) * (H - pad.top - pad.bottom);
  const points = data.map((d, i) => ({ x: x(i), y: y(d.value) }));
  const line = smoothPath(points);
  const area = points.length ? `${line} L${x(data.length - 1)},${y(0)} L${x(0)},${y(0)} Z` : "";
  const peak = data.findIndex((d) => d.value === max);
  const ticks = [0, niceMax / 2, niceMax];

  function onMove(e: React.PointerEvent<SVGSVGElement>) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect || data.length === 0) return;
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const step = (W - pad.left - pad.right) / Math.max(1, data.length - 1);
    setHover(Math.max(0, Math.min(data.length - 1, Math.round((px - pad.left) / step))));
  }

  const hp = hover !== null ? points[hover] : null;

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <ViewToggle table={table} onChange={setTable} />
      </div>
      {table ? (
        <DataTable data={data} unit={unit} labelHeader={labelHeader} />
      ) : (
        <div className="relative">
          <svg
            ref={svgRef}
            viewBox={`0 0 ${W} ${H}`}
            className="w-full touch-none select-none"
            onPointerMove={onMove}
            onPointerLeave={() => setHover(null)}
            role="img"
            aria-label={`${labelHeader} chart: ${data.map((d) => `${d.label} ${d.value}`).join(", ")}`}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.32" />
                <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
              </linearGradient>
            </defs>
            {ticks.map((t) => (
              <g key={t}>
                <line
                  x1={pad.left}
                  x2={W - pad.right}
                  y1={y(t)}
                  y2={y(t)}
                  stroke="currentColor"
                  className={t === 0 ? "text-foreground/20" : "text-foreground/[0.07]"}
                  strokeDasharray={t === 0 ? undefined : "3 4"}
                />
                <text x={pad.left - 8} y={y(t) + 4} textAnchor="end" className="fill-muted-foreground text-[11px] tabular-nums">
                  {t}
                </text>
              </g>
            ))}
            <path d={area} fill={`url(#${gradientId})`} />
            <path d={line} fill="none" stroke="var(--primary)" strokeWidth={2.5} strokeLinecap="round" />
            {data.map((d, i) => (
              <text key={d.label} x={x(i)} y={H - 8} textAnchor="middle" className="fill-muted-foreground text-[11px]">
                {d.label.slice(0, 3)}
              </text>
            ))}
            {hover === null && peak >= 0 ? (
              <g>
                <circle cx={points[peak].x} cy={points[peak].y} r={4.5} fill="var(--primary)" stroke="var(--card)" strokeWidth={2} />
                <text x={points[peak].x} y={points[peak].y - 12} textAnchor="middle" className="fill-foreground text-[12px] font-semibold">
                  peak {max}
                </text>
              </g>
            ) : null}
            {hp ? (
              <g>
                <line x1={hp.x} x2={hp.x} y1={pad.top - 6} y2={y(0)} stroke="currentColor" className="text-foreground/25" />
                <circle cx={hp.x} cy={hp.y} r={5} fill="var(--primary)" stroke="var(--card)" strokeWidth={2} />
              </g>
            ) : null}
          </svg>
          {hover !== null && hp ? (
            <div
              className="pointer-events-none absolute -top-1 z-10 -translate-x-1/2 whitespace-nowrap rounded-lg bg-foreground px-2.5 py-1 text-xs font-medium text-background shadow-lg"
              style={{ left: `${(hp.x / W) * 100}%` }}
            >
              {data[hover].label}: {data[hover].value} {unit}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
