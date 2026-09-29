"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

export type Datum = { label: string; value: number };

/** Chart/table switch: every chart ships a table view so values never depend on reading bars. */
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

/** Ranked horizontal bars (single series, one hue). Counts sit in a muted text column. */
export function HBarList({ data, unit, labelHeader }: { data: Datum[]; unit: string; labelHeader: string }) {
  const [table, setTable] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  const max = Math.max(1, ...data.map((d) => d.value));
  const total = data.reduce((n, d) => n + d.value, 0);

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <ViewToggle table={table} onChange={setTable} />
      </div>
      {table ? (
        <DataTable data={data} unit={unit} labelHeader={labelHeader} />
      ) : (
        <ul className="space-y-1">
          {data.map((d) => (
            <li
              key={d.label}
              onMouseEnter={() => setHover(d.label)}
              onMouseLeave={() => setHover(null)}
              className={cn(
                "relative grid grid-cols-[8.5rem_1fr_2.5rem] items-center gap-3 rounded-lg px-2 py-1.5 transition-colors",
                hover === d.label && "bg-muted/70",
              )}
            >
              <span className="truncate text-sm">{d.label}</span>
              <span className="h-3 w-full">
                <span
                  className="block h-3 rounded-r-[4px] bg-primary transition-opacity"
                  style={{ width: `${(d.value / max) * 100}%`, opacity: hover && hover !== d.label ? 0.45 : 1 }}
                />
              </span>
              <span className="text-right text-sm tabular-nums text-muted-foreground">{d.value}</span>
              {hover === d.label ? (
                <span className="pointer-events-none absolute left-36 top-full z-10 mt-1 whitespace-nowrap rounded-lg bg-foreground px-2.5 py-1 text-xs font-medium text-background shadow-lg">
                  {d.label}: {d.value} {unit} ({Math.round((d.value / total) * 100)}% of tags shown)
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Vertical columns over time (single series). Only the peak is direct-labelled; hover shows each value. */
export function ColumnChart({ data, unit, labelHeader }: { data: Datum[]; unit: string; labelHeader: string }) {
  const [table, setTable] = useState(false);
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...data.map((d) => d.value));

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <ViewToggle table={table} onChange={setTable} />
      </div>
      {table ? (
        <DataTable data={data} unit={unit} labelHeader={labelHeader} />
      ) : (
        <div>
          <div className="flex h-40 items-end gap-0.5 border-b border-foreground/15">
            {data.map((d, i) => (
              <div
                key={d.label}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                className="relative flex h-full flex-1 flex-col items-center justify-end"
              >
                {d.value === max || hover === i ? (
                  <span
                    className={cn(
                      "mb-1 whitespace-nowrap text-xs tabular-nums",
                      hover === i
                        ? "rounded-md bg-foreground px-1.5 py-0.5 font-medium text-background"
                        : "font-semibold text-foreground",
                    )}
                  >
                    {hover === i ? `${d.label}: ${d.value} ${unit}` : d.value}
                  </span>
                ) : null}
                <span
                  className="block w-full max-w-6 rounded-t-[4px] bg-primary transition-opacity"
                  style={{
                    height: `${(d.value / max) * 78}%`,
                    minHeight: d.value > 0 ? 3 : 0,
                    opacity: hover !== null && hover !== i ? 0.45 : 1,
                  }}
                />
              </div>
            ))}
          </div>
          <div className="mt-2 flex gap-0.5">
            {data.map((d) => (
              <span key={d.label} className="flex-1 text-center text-[11px] text-muted-foreground">
                {d.label.slice(0, 3)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
