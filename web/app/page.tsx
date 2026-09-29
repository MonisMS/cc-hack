"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeftRight, ArrowRight, Camera, FileText, MapPin } from "lucide-react";
import { NewProjectDialog } from "@/components/new-project-dialog";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { AssetCard, Project } from "@/lib/types";

type ProjectExtras = { thumbs: string[]; comparisons: number; reports: number };

function loadExtras(p: Project): Promise<ProjectExtras> {
  return Promise.all([
    api<{ items: AssetCard[] }>(`/api/assets?project_id=${p.id}&limit=3`),
    api<{ items: unknown[] }>(`/api/projects/${p.id}/comparisons`),
    api<{ items: unknown[] }>(`/api/projects/${p.id}/reports`),
  ]).then(([assets, comparisons, reports]) => ({
    thumbs: assets.items.map((a) => a.thumb_url).filter(Boolean) as string[],
    comparisons: comparisons.items.length,
    reports: reports.items.length,
  }));
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

function Sparkle({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 100 100" className={className} aria-hidden>
      <path d="M50 0 C53 40 60 47 100 50 C60 53 53 60 50 100 C47 60 40 53 0 50 C40 47 47 40 50 0Z" fill="currentColor" />
    </svg>
  );
}

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [extras, setExtras] = useState<Record<string, ProjectExtras>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<{ items: Project[] }>("/api/projects")
      .then((res) => {
        setProjects(res.items);
        return Promise.all(res.items.map((p) => loadExtras(p).then((x) => [p.id, x] as const)));
      })
      .then((pairs) => setExtras(Object.fromEntries(pairs)))
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load projects"));
  }, []);

  const loadedExtras = projects !== null && projects.every((p) => extras[p.id]);
  const sum = (f: (p: Project) => number) => (projects ? projects.reduce((n, p) => n + f(p), 0) : null);
  const sumExtras = (f: (x: ProjectExtras) => number) =>
    loadedExtras ? projects!.reduce((n, p) => n + f(extras[p.id]), 0) : null;
  const featured = projects?.length ? [...projects].sort((a, b) => b.asset_count - a.asset_count)[0] : null;

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Field evidence across all your projects.</p>
        </div>
        <NewProjectDialog onCreated={(project) => setProjects((prev) => [project, ...(prev ?? [])])} />
      </div>

      <section className="bg-grad-hero relative flex flex-wrap items-center justify-between gap-5 overflow-hidden rounded-3xl px-7 py-6 text-white">
        <Sparkle className="absolute right-[34%] -top-3 size-16 text-white/20" />
        <Sparkle className="absolute right-[22%] bottom-2 size-8 text-white/20" />
        <div className="relative">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-white/75">Field evidence platform</p>
          <h2 className="mt-1.5 text-2xl font-semibold tracking-tight">Turn field photos into proof of impact</h2>
          <p className="mt-1 text-sm text-white/80">
            Auto-tag, compare before and after, and publish reports, all traceable to the source photo.
          </p>
        </div>
        {featured ? (
          <Button
            variant="dark"
            size="lg"
            className="relative pr-1.5"
            nativeButton={false}
            render={
              <Link href={`/projects/${featured.id}`}>
                Open {featured.name}
                <span className="grid size-8 place-items-center rounded-full bg-white text-foreground">
                  <ArrowRight className="size-4" />
                </span>
              </Link>
            }
          />
        ) : null}
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Photos analysed" value={sum((p) => p.ready_count)} sub="tagged, dated and searchable" icon={Camera} gradient="sunset" />
        <StatCard label="Sites covered" value={sum((p) => p.site_count)} sub="photos auto-assigned by GPS" icon={MapPin} gradient="ocean" />
        <StatCard label="Before / after comparisons" value={sumExtras((x) => x.comparisons)} sub="with estimated green-cover change" icon={ArrowLeftRight} gradient="mint" />
        <StatCard label="Impact reports" value={sumExtras((x) => x.reports)} sub="with campaign kits and lineage" icon={FileText} gradient="lilac" />
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">Your projects</h2>

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {projects === null && !error ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-64 rounded-2xl" />
            ))}
          </div>
        ) : null}

        {projects && projects.length === 0 ? (
          <p className="text-sm text-muted-foreground">No projects yet. Create one to get started.</p>
        ) : null}

        {projects && projects.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => {
              const x = extras[p.id];
              const pct = p.asset_count ? Math.round((p.ready_count / p.asset_count) * 100) : 0;
              return (
                <Link key={p.id} href={`/projects/${p.id}`} className="group">
                  <Card className="h-full gap-4 px-4 pt-4 transition-transform group-hover:-translate-y-0.5">
                    <div className="grid h-28 grid-cols-3 gap-2">
                      {[0, 1, 2].map((i) =>
                        x?.thumbs[i] ? (
                          <img key={i} src={x.thumbs[i]} alt="" className="h-full w-full rounded-xl object-cover" />
                        ) : (
                          <div key={i} className="rounded-xl bg-muted" />
                        ),
                      )}
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-base font-semibold tracking-tight">{p.name}</h3>
                      <p className="line-clamp-2 text-sm text-muted-foreground">
                        {p.description ?? (p.started_on ? `Started ${p.started_on}` : "Field evidence project")}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground">
                        <MapPin className="size-3.5" /> {plural(p.site_count, "site")}
                      </span>
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground">
                        <Camera className="size-3.5" /> {plural(p.asset_count, "photo")}
                      </span>
                      {x ? (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground">
                          <FileText className="size-3.5" /> {plural(x.reports, "report")}
                        </span>
                      ) : null}
                      {p.failed_count > 0 ? (
                        <span className="rounded-full bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive">
                          {p.failed_count} failed
                        </span>
                      ) : null}
                    </div>
                    <div className="space-y-1.5 pb-1">
                      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {p.ready_count} of {p.asset_count} photos analysed
                      </p>
                    </div>
                  </Card>
                </Link>
              );
            })}
          </div>
        ) : null}
      </section>
    </div>
  );
}
