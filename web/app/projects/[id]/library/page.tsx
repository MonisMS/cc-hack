"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
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
import type { AssetCard, AssetStatus, Site } from "@/lib/types";

const ALL = "all";

export default function LibraryPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [sites, setSites] = useState<Site[]>([]);
  const [siteId, setSiteId] = useState(ALL);
  const [status, setStatus] = useState<AssetStatus | typeof ALL>(ALL);
  const [tagInput, setTagInput] = useState("");
  const [tag, setTag] = useState("");
  const [assets, setAssets] = useState<AssetCard[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialLoaded, setInitialLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    api<{ items: Site[] }>(`/api/projects/${projectId}/sites`)
      .then((res) => setSites(res.items))
      .catch(() => {});
  }, [projectId]);

  function buildQuery(cursor?: string | null) {
    if (!projectId) return null;
    const params = new URLSearchParams({ project_id: projectId, limit: "30" });
    if (siteId !== ALL) params.set("site_id", siteId);
    if (status !== ALL) params.set("status", status);
    if (tag) params.set("tag", tag);
    if (cursor) params.set("cursor", cursor);
    return params.toString();
  }

  const loadMore = useCallback(
    (cursor: string) => {
      const query = buildQuery(cursor);
      if (!query) return;
      setLoading(true);
      api<{ items: AssetCard[]; next_cursor: string | null }>(`/api/assets?${query}`)
        .then((res) => {
          setAssets((prev) => [...prev, ...res.items]);
          setNextCursor(res.next_cursor);
          setError(null);
        })
        .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load assets"))
        .finally(() => setLoading(false));
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [projectId, siteId, status, tag],
  );

  // First page: refetch whenever the project or a filter changes.
  useEffect(() => {
    const query = buildQuery(null);
    if (!query) return;
    api<{ items: AssetCard[]; next_cursor: string | null }>(`/api/assets?${query}`)
      .then((res) => {
        setAssets(res.items);
        setNextCursor(res.next_cursor);
        setError(null);
      })
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load assets"))
      .finally(() => setInitialLoaded(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, siteId, status, tag]);

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="type-display">Library</h1>
        <p className="text-muted-foreground">All uploaded photos in this project.</p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Site</span>
          <Select value={siteId} onValueChange={(v) => setSiteId(v ?? ALL)}>
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
          <span className="text-xs font-medium text-muted-foreground">Status</span>
          <Select value={status} onValueChange={(v) => setStatus((v as AssetStatus | typeof ALL) ?? ALL)}>
            <SelectTrigger className="w-40">
              <SelectValue>
                {() =>
                  status === ALL
                    ? "All statuses"
                    : status.charAt(0).toUpperCase() + status.slice(1)
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="ready">Ready</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <form
          className="grid gap-1.5"
          onSubmit={(e) => {
            e.preventDefault();
            setTag(tagInput.trim().toLowerCase());
          }}
        >
          <span className="text-xs font-medium text-muted-foreground">Tag</span>
          <div className="flex gap-2">
            <Input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              placeholder="e.g. flood"
              className="w-40"
            />
            <Button type="submit" variant="outline">
              Filter
            </Button>
          </div>
        </form>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {!initialLoaded ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="aspect-4/3" />
          ))}
        </div>
      ) : null}

      {initialLoaded && assets.length === 0 && !error ? (
        <p className="text-sm text-muted-foreground">No assets yet — upload some.</p>
      ) : null}

      <AssetGrid assets={assets} />

      {nextCursor ? (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => loadMore(nextCursor)} disabled={loading}>
            {loading ? "Loading..." : "Load more"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
