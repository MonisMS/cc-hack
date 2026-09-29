"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { X } from "lucide-react";
import { AssetGrid } from "@/components/asset-grid";
import { EmptyState, PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { AssetCard, Project, Site } from "@/lib/types";

const ALL = "all";
const PAGE = 30;

type Page = { items: AssetCard[]; next_cursor: string | null };

function LibraryInner() {
  const params = useSearchParams();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [projectId, setProjectId] = useState(params.get("project") ?? "");
  const [sites, setSites] = useState<Site[]>([]);
  const [siteId, setSiteId] = useState(params.get("site") ?? ALL);
  const [tag, setTag] = useState(params.get("tag") ?? "");
  const [assets, setAssets] = useState<AssetCard[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<{ items: Project[] }>("/api/projects")
      .then((res) => {
        setProjects(res.items);
        // Default to the project with the most photos.
        setProjectId((cur) => cur || ([...res.items].sort((a, b) => b.asset_count - a.asset_count)[0]?.id ?? ""));
      })
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load projects"));
  }, []);

  useEffect(() => {
    if (!projectId) return;
    api<{ items: Site[] }>(`/api/projects/${projectId}/sites`)
      .then((res) => setSites(res.items))
      .catch(() => setSites([]));
  }, [projectId]);

  function query(cursor?: string | null) {
    const q = new URLSearchParams({ project_id: projectId, limit: String(PAGE) });
    if (siteId !== ALL) q.set("site_id", siteId);
    if (tag) q.set("tag", tag);
    if (cursor) q.set("cursor", cursor);
    return q.toString();
  }

  useEffect(() => {
    if (!projectId) return;
    api<Page>(`/api/assets?${query()}`)
      .then((res) => {
        setAssets(res.items);
        setNextCursor(res.next_cursor);
        setError(null);
      })
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load photos"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, siteId, tag]);

  function loadMore() {
    if (!nextCursor) return;
    setLoadingMore(true);
    api<Page>(`/api/assets?${query(nextCursor)}`)
      .then((res) => {
        setAssets((prev) => [...(prev ?? []), ...res.items]);
        setNextCursor(res.next_cursor);
      })
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load photos"))
      .finally(() => setLoadingMore(false));
  }

  // Most common AI tags among the photos shown, as one-click filters.
  const tagCounts = Object.entries(
    (assets ?? []).reduce<Record<string, number>>((acc, a) => {
      for (const t of a.tags) acc[t.tag] = (acc[t.tag] ?? 0) + 1;
      return acc;
    }, {}),
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const project = projects?.find((p) => p.id === projectId);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <PageHeader
        title="Library"
        subtitle={
          project
            ? `${project.asset_count} photos in ${project.name}, tagged automatically by AI.`
            : "Every photo, tagged automatically by AI."
        }
      />

      <Card>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Project</span>
              <Select
                value={projectId}
                onValueChange={(v) => {
                  setProjectId(v ?? "");
                  setSiteId(ALL);
                  setAssets(null);
                }}
              >
                <SelectTrigger className="w-60 rounded-full">
                  <SelectValue>{() => project?.name ?? "Choose a project"}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {(projects ?? []).map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Site</span>
              <Select value={siteId} onValueChange={(v) => setSiteId(v ?? ALL)}>
                <SelectTrigger className="w-48 rounded-full">
                  <SelectValue>
                    {() => (siteId === ALL ? "All sites" : sites.find((s) => s.id === siteId)?.name ?? "All sites")}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>All sites</SelectItem>
                  {sites.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {tag ? (
              <button
                type="button"
                onClick={() => setTag("")}
                className="inline-flex h-9 items-center gap-1.5 rounded-full bg-primary px-3.5 text-sm font-medium text-primary-foreground"
              >
                tag: {tag} <X className="size-3.5" />
              </button>
            ) : null}
          </div>

          {tagCounts.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground">AI tags:</span>
              {tagCounts.map(([t, n]) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTag(t === tag ? "" : t)}
                  className={
                    t === tag
                      ? "rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground"
                      : "rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
                  }
                >
                  {t.replace(/_/g, " ")} · {n}
                </button>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {assets === null && !error ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {Array.from({ length: 10 }, (_, i) => (
            <Skeleton key={i} className="aspect-4/3 rounded-2xl" />
          ))}
        </div>
      ) : null}

      {assets?.length === 0 ? <EmptyState>No photos match these filters.</EmptyState> : null}

      {assets && assets.length > 0 ? <AssetGrid assets={assets} /> : null}

      {nextCursor ? (
        <div className="flex justify-center">
          <Button variant="outline" onClick={loadMore} disabled={loadingMore}>
            {loadingMore ? "Loading..." : "Load more"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export default function LibraryPage() {
  return (
    <Suspense>
      <LibraryInner />
    </Suspense>
  );
}
