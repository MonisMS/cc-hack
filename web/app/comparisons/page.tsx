"use client";

import Link from "next/link";
import { ArrowLeftRight, ArrowUpRight, CalendarDays, TrendingDown, TrendingUp, Trophy } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Comparison } from "@/lib/types";
import { useAcrossProjects } from "@/lib/workspace";

function Delta({ value }: { value: number | null }) {
  if (value == null) return <span className="text-xs text-muted-foreground">no estimate</span>;
  const up = value > 0;
  const flat = value === 0;
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <span
      className={
        flat
          ? "inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-semibold text-muted-foreground"
          : up
            ? "inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700"
            : "inline-flex items-center gap-1 rounded-full bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-700"
      }
    >
      {flat ? null : <Icon className="size-3.5" />}
      {up ? "+" : ""}
      {value} pts green
    </span>
  );
}

export default function ComparisonsPage() {
  const { items, error } = useAcrossProjects<Comparison>((id) => `/api/projects/${id}/comparisons`);
  const sorted = items ? [...items].sort((a, b) => b.created_at.localeCompare(a.created_at)) : null;
  const ready = items?.filter((c) => c.delta_green_pct_rounded != null) ?? [];
  const best = ready.length ? ready.reduce((m, c) => (c.delta_green_pct_rounded! > m.delta_green_pct_rounded! ? c : m)) : null;
  const avgDays = ready.length ? Math.round(ready.reduce((n, c) => n + (c.days_apart ?? 0), 0) / ready.length) : null;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <PageHeader
        title="Comparisons"
        subtitle="Before and after photos of the same site, with the estimated change in green cover."
        action={
          <Button nativeButton={false} render={<Link href="/sites">New comparison</Link>} />
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Comparisons" value={items ? items.length : null} sub="across all projects" icon={ArrowLeftRight} gradient="lilac" />
        <StatCard
          label="Biggest gain"
          value={items ? (best ? `${best.delta_green_pct_rounded! > 0 ? "+" : ""}${best.delta_green_pct_rounded}` : "—") : null}
          sub={best ? `points of green cover at ${best.site_name}` : "no estimates yet"}
          icon={Trophy}
          gradient="mint"
        />
        <StatCard
          label="Average time apart"
          value={items ? (avgDays != null ? avgDays : "—") : null}
          sub="days between before and after"
          icon={CalendarDays}
          gradient="ocean"
        />
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {sorted === null && !error ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-72 rounded-2xl" />
          ))}
        </div>
      ) : null}

      {sorted?.length === 0 ? (
        <EmptyState>
          No comparisons yet. Open <Link href="/sites" className="text-primary hover:underline">Sites</Link> and pick a
          before/after pair.
        </EmptyState>
      ) : null}

      {sorted && sorted.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {sorted.map((c) => (
            <Link key={c.id} href={`/comparisons/${c.id}`} className="group">
              <Card className="h-full gap-0 py-0 transition-all group-hover:-translate-y-0.5 group-hover:shadow-[0_18px_40px_-18px_rgb(60_45_160/0.3)]">
                <div className="relative grid grid-cols-2 gap-0.5 overflow-hidden">
                  {[
                    { url: c.before.thumb_url, label: "Before", date: c.before.captured_at },
                    { url: c.after.thumb_url, label: "After", date: c.after.captured_at },
                  ].map((side) => (
                    <div key={side.label} className="relative aspect-4/3 overflow-hidden bg-muted">
                      <img src={side.url} alt="" loading="lazy" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]" />
                      <span className="absolute left-2 top-2 rounded-full bg-black/55 px-2 py-0.5 text-[11px] font-medium text-white backdrop-blur-sm">
                        {side.label}
                        {side.date ? ` · ${side.date.slice(0, 10)}` : ""}
                      </span>
                    </div>
                  ))}
                  <span className="absolute left-1/2 top-1/2 grid size-9 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-white text-foreground shadow-md">
                    <ArrowLeftRight className="size-4" />
                  </span>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-3 p-5">
                  <div className="space-y-1">
                    <h3 className="type-title flex items-center gap-1.5">
                      {c.site_name}
                      <ArrowUpRight className="size-4 text-muted-foreground transition-colors group-hover:text-primary" />
                    </h3>
                    <p className="text-[13px] text-muted-foreground">
                      {c.project.name}
                      {c.days_apart != null ? ` · ${c.days_apart} days apart` : ""}
                      {c.before_green_pct_rounded != null
                        ? ` · ${c.before_green_pct_rounded}% → ${c.after_green_pct_rounded}%`
                        : ""}
                    </p>
                  </div>
                  {c.status === "ready" ? <Delta value={c.delta_green_pct_rounded} /> : <StatusBadge status={c.status} />}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
