"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { NewProjectDialog } from "@/components/new-project-dialog";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { Project } from "@/lib/types";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<{ items: Project[] }>("/api/projects")
      .then((res) => setProjects(res.items))
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load projects"));
  }, []);

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-muted-foreground">Your FieldProof projects.</p>
        </div>
        <NewProjectDialog onCreated={(project) => setProjects((prev) => [project, ...(prev ?? [])])} />
      </div>

      {error ? <p className="text-destructive text-sm">{error}</p> : null}

      {projects === null && !error ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : null}

      {projects && projects.length === 0 ? (
        <p className="text-muted-foreground text-sm">No projects yet — create one to get started.</p>
      ) : null}

      {projects && projects.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`}>
              <Card className="h-full transition-colors hover:border-primary/50">
                <CardHeader>
                  <CardTitle>{p.name}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {p.description ? (
                    <p className="text-sm text-muted-foreground line-clamp-2">{p.description}</p>
                  ) : null}
                  <div className="flex flex-wrap gap-2 text-xs">
                    <Badge variant="secondary">{p.site_count} sites</Badge>
                    <Badge variant="secondary">{p.asset_count} assets</Badge>
                    <Badge variant="secondary">{p.ready_count} ready</Badge>
                    {p.failed_count > 0 ? <Badge variant="destructive">{p.failed_count} failed</Badge> : null}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
