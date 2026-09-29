"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeftRight, ArrowRight, Camera, FileText, MapPin } from "lucide-react";
import { DashboardInsights } from "@/components/dashboard-insights";
import { NewProjectDialog } from "@/components/new-project-dialog";
import { PageHeader } from "@/components/page-header";
import { loadProjectExtras, ProjectCard, type ProjectExtras } from "@/components/project-card";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { Project } from "@/lib/types";

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
        return Promise.all(res.items.map((p) => loadProjectExtras(p).then((x) => [p.id, x] as const)));
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
      <PageHeader
        title="Dashboard"
        subtitle="Field evidence across all your projects."
        action={<NewProjectDialog onCreated={(project) => setProjects((prev) => [project, ...(prev ?? [])])} />}
      />

      <section className="bg-grad-hero relative flex flex-wrap items-center justify-between gap-5 overflow-hidden rounded-3xl px-8 py-7 text-white">
        <Sparkle className="absolute right-[34%] -top-3 size-16 text-white/20" />
        <Sparkle className="absolute right-[22%] bottom-2 size-8 text-white/20" />
        <div className="relative">
          <p className="type-eyebrow text-white/80">Field evidence platform</p>
          <h2 className="mt-2 text-[28px] font-bold leading-tight tracking-[-0.025em]">Turn field photos into proof of impact</h2>
          <p className="mt-1.5 text-[15px] text-white/85">
            Auto-tag, compare before and after, and publish reports, all traceable to the source photo.
          </p>
        </div>
        {featured ? (
          <Button
            size="lg"
            className="relative bg-white pr-1.5 font-semibold text-emerald-950 shadow-[0_10px_28px_-12px_rgb(0_0_0/0.45)] hover:bg-white/90"
            nativeButton={false}
            render={
              <Link href={`/projects/${featured.id}`}>
                Open {featured.name}
                <span className="grid size-8 place-items-center rounded-full bg-emerald-900 text-white">
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

      {featured ? <DashboardInsights key={featured.id} project={featured} /> : null}

      <section className="space-y-4">
        <h2 className="type-title">Your projects</h2>

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
            {projects.map((p) => (
              <ProjectCard key={p.id} project={p} extras={extras[p.id]} />
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
