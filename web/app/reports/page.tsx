"use client";

import Link from "next/link";
import { Camera, FileText, Printer } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/page-header";
import { MetaLine, PhotoMosaic } from "@/components/photo-mosaic";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Report } from "@/lib/types";
import { plural, useAcrossProjects } from "@/lib/workspace";

function thumbs(r: Report): string[] {
  const urls: string[] = [];
  for (const item of r.items) {
    if (item.comparison) urls.push(item.comparison.after.thumb_url);
    else if (item.asset) urls.push(item.asset.thumb_url);
    if (urls.length === 4) break;
  }
  return urls;
}

export default function ReportsPage() {
  const { projects, items, error } = useAcrossProjects<Report>((id) => `/api/projects/${id}/reports`);
  // Reports are created from a project page; send "New report" to the main project.
  const main = projects?.length ? [...projects].sort((a, b) => b.asset_count - a.asset_count)[0] : null;
  const sorted = items ? [...items].sort((a, b) => b.created_at.localeCompare(a.created_at)) : null;
  const evidence = items?.reduce((n, r) => n + r.items.length, 0) ?? null;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <PageHeader
        title="Reports"
        subtitle="Impact reports built from field evidence: numbers, summary, before/after proof and a campaign kit."
        action={<Button nativeButton={false} render={<Link href={main ? `/projects/${main.id}` : "/projects"}>New report</Link>} />}
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Reports" value={items ? items.length : null} sub="across all projects" icon={FileText} gradient="sunset" />
        <StatCard label="Evidence items" value={evidence} sub="photos and comparisons cited" icon={Camera} gradient="ocean" />
        <StatCard
          label="Campaign kits"
          value={items ? items.filter((r) => r.status === "ready").length : null}
          sub="social square, story and collage each"
          icon={Printer}
          gradient="lilac"
        />
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {sorted === null && !error ? (
        <div className="space-y-4">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-40 rounded-2xl" />
          ))}
        </div>
      ) : null}

      {sorted?.length === 0 ? (
        <EmptyState>
          No reports yet. Open a <Link href="/projects" className="text-primary hover:underline">project</Link> and click
          New report.
        </EmptyState>
      ) : null}

      {sorted && sorted.length > 0 ? (
        <div className="space-y-4">
          {sorted.map((r) => {
            const comparisons = r.items.filter((i) => i.kind === "comparison").length;
            const photos = r.items.filter((i) => i.kind === "asset").length;
            return (
              <Card key={r.id} className="flex-row flex-wrap items-stretch gap-0 py-0 sm:flex-nowrap">
                <PhotoMosaic urls={thumbs(r)} layout="square" className="aspect-square w-full sm:w-44" />
                <div className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-4 p-5">
                  <div className="min-w-0 space-y-1.5">
                    <p className="type-eyebrow text-muted-foreground">
                      {r.date_from ?? "?"} → {r.date_to ?? "?"}
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="type-title">{r.summary?.headline ?? "Report"}</h3>
                      {r.status !== "ready" ? <StatusBadge status={r.status} /> : null}
                    </div>
                    <MetaLine
                      items={[
                        r.project.name,
                        plural(comparisons, "before/after"),
                        plural(photos, "evidence photo"),
                        `created ${r.created_at.slice(0, 10)}`,
                      ]}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" nativeButton={false} render={<Link href={`/reports/${r.id}/print`}>Print</Link>} />
                    <Button nativeButton={false} render={<Link href={`/reports/${r.id}`}>Open report</Link>} />
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
