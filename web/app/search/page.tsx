"use client";

import { useEffect, useState } from "react";
import { AssetGrid } from "@/components/asset-grid";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { Project, SearchHit, Site } from "@/lib/types";

const ALL = "all";

const EXAMPLE_QUERIES = [
  "saplings being planted",
  "flooded road",
  "solar panels",
  "children in a classroom",
];

export default function SearchPage() {
  const [queryInput, setQueryInput] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState(ALL);
  const [sites, setSites] = useState<Site[]>([]);
  const [siteId, setSiteId] = useState(ALL);
  const [tagInput, setTagInput] = useState("");
  const [tag, setTag] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<{ items: Project[] }>("/api/projects")
      .then((res) => setProjects(res.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (projectId === ALL) return;
    api<{ items: Site[] }>(`/api/projects/${projectId}/sites`)
      .then((res) => setSites(res.items))
      .catch(() => setSites([]));
  }, [projectId]);

  function handleProjectChange(value: string | null) {
    setProjectId(value ?? ALL);
    setSites([]);
    setSiteId(ALL);
  }

  function runSearch(q: string, proj: string, site: string, t: string) {
    setLoading(true);
    setError(null);
    api<{ items: SearchHit[] }>("/api/search", {
      method: "POST",
      body: JSON.stringify({
        query: q,
        project_id: proj === ALL ? null : proj,
        site_id: site === ALL ? null : site,
        tag: t || null,
      }),
    })
      .then((res) => {
        setHits(res.items);
        setSearched(true);
      })
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Search failed"))
      .finally(() => setLoading(false));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = queryInput.trim();
    const t = tagInput.trim().toLowerCase();
    setTag(t);
    runSearch(q, projectId, siteId, t);
  }

  function handleExample(q: string) {
    setQueryInput(q);
    runSearch(q, projectId, siteId, tag);
  }

  const scores = Object.fromEntries(hits.map((h) => [h.asset.id, h.score]));

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Search</h1>
        <p className="text-muted-foreground">Find photos by what&apos;s in them.</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Query</span>
          <Input
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            placeholder="e.g. saplings being planted"
            className="w-72"
          />
        </div>

        <div className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Project</span>
          <Select value={projectId} onValueChange={handleProjectChange}>
            <SelectTrigger className="w-44">
              <SelectValue>
                {() => (projectId === ALL ? "All projects" : projects.find((p) => p.id === projectId)?.name ?? "All projects")}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All projects</SelectItem>
              {projects.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Site</span>
          <Select value={siteId} onValueChange={(v) => setSiteId(v ?? ALL)} disabled={projectId === ALL}>
            <SelectTrigger className="w-44">
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

        <div className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Tag</span>
          <Input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="e.g. flood"
            className="w-36"
          />
        </div>

        <Button type="submit" disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </Button>
      </form>

      <div className="flex flex-wrap gap-2">
        {EXAMPLE_QUERIES.map((q) => (
          <Button key={q} type="button" variant="outline" size="sm" onClick={() => handleExample(q)}>
            {q}
          </Button>
        ))}
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="aspect-4/3" />
          ))}
        </div>
      ) : null}

      {!loading && searched && hits.length === 0 && !error ? (
        <p className="text-sm text-muted-foreground">No matches — try a different query.</p>
      ) : null}

      {!loading ? <AssetGrid assets={hits.map((h) => h.asset)} scores={scores} /> : null}
    </div>
  );
}
