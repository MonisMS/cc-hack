"use client";

import { useEffect, useState } from "react";
import { NewProjectDialog } from "@/components/new-project-dialog";
import { EmptyState, PageHeader } from "@/components/page-header";
import { loadProjectExtras, ProjectCard, type ProjectExtras } from "@/components/project-card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { Project } from "@/lib/types";

export default function ProjectsPage() {
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

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <PageHeader
        title="Projects"
        subtitle="Each project is one field initiative: its sites, photos, comparisons and reports."
        action={<NewProjectDialog onCreated={(project) => setProjects((prev) => [project, ...(prev ?? [])])} />}
      />

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {projects === null && !error ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-64 rounded-2xl" />
          ))}
        </div>
      ) : null}

      {projects?.length === 0 ? <EmptyState>No projects yet. Create one to get started.</EmptyState> : null}

      {projects && projects.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <ProjectCard key={p.id} project={p} extras={extras[p.id]} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
