"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, GraduationCap, Search, Sprout, Sun, Waves, type LucideIcon } from "lucide-react";
import { AssetGrid } from "@/components/asset-grid";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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

const EXAMPLE_QUERIES: { q: string; icon: LucideIcon; gradient: string }[] = [
  { q: "saplings being planted", icon: Sprout, gradient: "bg-grad-mint" },
  { q: "flooded road", icon: Waves, gradient: "bg-grad-ocean" },
  { q: "solar panels", icon: Sun, gradient: "bg-grad-sunset" },
  { q: "children in a classroom", icon: GraduationCap, gradient: "bg-grad-lilac" },
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
  const [lastQuery, setLastQuery] = useState("");

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
    setLastQuery(q);
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
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <p className="text-sm text-muted-foreground">
          Describe what you&apos;re looking for in plain English. The AI matches what&apos;s in the photo, not just its tags.
        </p>
      </div>

      <Card>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  placeholder="e.g. saplings being planted"
                  className="h-12 rounded-full pl-12 text-base md:text-base"
                />
              </div>
              <Button type="submit" size="lg" className="h-12 px-6" disabled={loading}>
                {loading ? "Searching..." : "Search"}
              </Button>
            </div>

            <div className="flex flex-wrap items-end gap-3">
              <div className="grid gap-1.5">
                <span className="text-xs font-medium text-muted-foreground">Project</span>
                <Select value={projectId} onValueChange={handleProjectChange}>
                  <SelectTrigger className="w-52 rounded-full">
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
                  <SelectTrigger className="w-44 rounded-full">
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
                  className="w-40 rounded-full"
                />
              </div>

              {searched ? (
                <div className="ml-auto flex flex-wrap items-center gap-2">
                  <span className="text-xs text-muted-foreground">Try:</span>
                  {EXAMPLE_QUERIES.map(({ q }) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => handleExample(q)}
                      className="rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          </form>
        </CardContent>
      </Card>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {!searched && !loading ? (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-tight">Try a search</h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {EXAMPLE_QUERIES.map(({ q, icon: Icon, gradient }) => (
              <button
                key={q}
                type="button"
                onClick={() => handleExample(q)}
                className={`${gradient} group flex h-40 flex-col justify-between rounded-3xl p-5 text-left transition-transform hover:-translate-y-0.5`}
              >
                <div className="flex w-full items-start justify-between">
                  <span className="grid size-10 place-items-center rounded-xl bg-white/45 backdrop-blur-sm">
                    <Icon className="size-[18px]" />
                  </span>
                  <ArrowUpRight className="size-5 opacity-60 transition-opacity group-hover:opacity-100" />
                </div>
                <div>
                  <p className="text-xs text-foreground/70">Search for</p>
                  <p className="text-lg font-medium leading-snug">&ldquo;{q}&rdquo;</p>
                </div>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="aspect-4/3 rounded-2xl" />
          ))}
        </div>
      ) : null}

      {!loading && searched && hits.length === 0 && !error ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No matches. Try a different description or clear the filters.
          </CardContent>
        </Card>
      ) : null}

      {!loading && searched && hits.length > 0 ? (
        <section className="space-y-3">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{hits.length} photos</span>
            {lastQuery ? <> matching &ldquo;{lastQuery}&rdquo;</> : null}, best match first
          </p>
          <AssetGrid assets={hits.map((h) => h.asset)} scores={scores} />
        </section>
      ) : null}
    </div>
  );
}
