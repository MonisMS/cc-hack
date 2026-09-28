"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { AssetGrid } from "@/components/asset-grid";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { AssetCard, AssetStatus, Site } from "@/lib/types";

const STATUS_OPTIONS: AssetStatus[] = ["pending", "processing", "ready", "failed"];

export default function LibraryPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [sites, setSites] = useState<Site[]>([]);
  const [siteId, setSiteId] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [tag, setTag] = useState("");

  const [assets, setAssets] = useState<AssetCard[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    api<{ items: Site[] }>(`/api/projects/${projectId}/sites`)
      .then((res) => setSites(res.items))
      .catch(() => {});
  }, [projectId]);

  const buildQuery = useCallback(
    (cursor?: string) => {
      const params = new URLSearchParams({ project_id: projectId, limit: "60" });
      if (siteId) params.set("site_id", siteId);
      if (status) params.set("status", status);
      if (tag.trim()) params.set("tag", tag.trim());
      if (cursor) params.set("cursor", cursor);
      return params.toString();
    },
    [projectId, siteId, status, tag],
  );

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const res = await api<{ items: AssetCard[]; next_cursor: string | null }>(`/api/assets?${buildQuery()}`);
        if (cancelled) return;
        setAssets(res.items);
        setNextCursor(res.next_cursor);
      } catch (err) {
        if (cancelled) return;
        toast.error(err instanceof ApiErr ? err.message : "Could not load assets");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [projectId, buildQuery]);

  async function loadMore() {
    if (!nextCursor) return;
    setLoadingMore(true);
    try {
      const res = await api<{ items: AssetCard[]; next_cursor: string | null }>(`/api/assets?${buildQuery(nextCursor)}`);
      setAssets((prev) => [...prev, ...res.items]);
      setNextCursor(res.next_cursor);
    } catch (err) {
      toast.error(err instanceof ApiErr ? err.message : "Could not load more assets");
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Library</h1>

      <div className="flex flex-wrap items-center gap-3">
        <Select value={siteId || "all"} onValueChange={(v) => setSiteId(v === "all" || !v ? "" : v)}>
          <SelectTrigger>
            <SelectValue placeholder="All sites" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All sites</SelectItem>
            {sites.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {s.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={status || "all"} onValueChange={(v) => setStatus(v === "all" || !v ? "" : v)}>
          <SelectTrigger>
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Input placeholder="Filter by tag" value={tag} onChange={(e) => setTag(e.target.value)} className="max-w-40" />
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square" />
          ))}
        </div>
      ) : (
        <>
          <AssetGrid assets={assets} />
          {nextCursor ? (
            <div className="flex justify-center">
              <Button variant="outline" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? "Loading..." : "Load more"}
              </Button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
