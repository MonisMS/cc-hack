"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { LineagePanel } from "@/components/lineage-panel";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { AssetDetail, Site, Tag } from "@/lib/types";

const SOURCE_LABEL: Record<Tag["source"], string> = {
  clip: "Suggested",
  cld_detection: "Detected",
  manual: "Manual",
};

export default function AssetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newTag, setNewTag] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [reprocessing, setReprocessing] = useState(false);

  async function refresh() {
    const a = await api<AssetDetail>(`/api/assets/${id}`);
    setAsset(a);
  }

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        await refresh();
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiErr ? err.message : "Could not load asset");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!asset) return;
    let cancelled = false;
    api<{ items: Site[] }>(`/api/projects/${asset.project_id}/sites`)
      .then((res) => {
        if (!cancelled) setSites(res.items);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asset?.project_id]);

  async function patch(body: Record<string, unknown>) {
    try {
      const updated = await api<AssetDetail>(`/api/assets/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setAsset(updated);
      toast.success("Saved");
    } catch (err) {
      toast.error(err instanceof ApiErr ? err.message : "Could not save changes");
    }
  }

  async function addTag() {
    if (!newTag.trim()) return;
    await patch({ add_tags: [newTag.trim().toLowerCase()] });
    setNewTag("");
  }

  async function removeTag(tag: string) {
    await patch({ remove_tags: [tag] });
  }

  async function setLocation() {
    const latNum = Number(lat);
    const lngNum = Number(lng);
    if (Number.isNaN(latNum) || Number.isNaN(lngNum)) return;
    await patch({ lat: latNum, lng: lngNum });
    setLat("");
    setLng("");
  }

  async function moveToSite(siteId: string) {
    await patch({ site_id: siteId });
  }

  async function reprocess() {
    if (!asset) return;
    setReprocessing(true);
    try {
      await api(`/api/assets/${asset.id}/reprocess`, { method: "POST" });
      toast.success("Reprocessing queued");
      await refresh();
    } catch (err) {
      toast.error(err instanceof ApiErr ? err.message : "Could not reprocess");
    } finally {
      setReprocessing(false);
    }
  }

  if (error) {
    return <p className="p-8 text-destructive text-sm">{error}</p>;
  }

  if (!asset) {
    return (
      <div className="p-8 space-y-4 max-w-3xl">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="aspect-video" />
      </div>
    );
  }

  const tagsBySource: Record<Tag["source"], Tag[]> = { clip: [], cld_detection: [], manual: [] };
  for (const t of asset.tags) tagsBySource[t.source].push(t);

  return (
    <div className="p-8 space-y-6 max-w-3xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{asset.site_name ?? "Unassigned"}</h1>
          <p className="text-sm text-muted-foreground">{asset.captured_at ? new Date(asset.captured_at).toLocaleString() : "No capture date"}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={asset.status} />
          <LineagePanel entityType="asset" entityId={asset.id} />
        </div>
      </div>

      {asset.error ? <p className="text-sm text-destructive">{asset.error}</p> : null}

      <img src={asset.compare_url} alt="" className="w-full rounded-lg border object-cover" />

      <Card>
        <CardHeader>
          <CardTitle>Tags</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {(Object.keys(tagsBySource) as Tag["source"][]).map((source) =>
            tagsBySource[source].length > 0 ? (
              <div key={source}>
                <div className="text-xs font-medium text-muted-foreground mb-1">{SOURCE_LABEL[source]}</div>
                <div className="flex flex-wrap gap-1.5">
                  {tagsBySource[source].map((t) => (
                    <Badge key={t.tag} variant={source === "manual" ? "default" : source === "clip" ? "secondary" : "outline"}>
                      {t.tag}
                      {source === "manual" ? (
                        <button type="button" onClick={() => removeTag(t.tag)} className="ml-1">
                          ×
                        </button>
                      ) : null}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null,
          )}
          <div className="flex gap-2 pt-1">
            <Input
              placeholder="Add a tag"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addTag()}
              className="max-w-48"
            />
            <Button type="button" variant="outline" onClick={addTag}>
              Add
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Location & site</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {asset.lat_r != null && asset.lng_r != null ? `${asset.lat_r}, ${asset.lng_r}` : "No location"}
            {asset.location_source ? ` · source: ${asset.location_source}` : ""}
          </p>

          <div className="flex items-end gap-2">
            <div className="grid gap-1.5">
              <Label htmlFor="asset-lat">Latitude</Label>
              <Input id="asset-lat" type="number" step="any" value={lat} onChange={(e) => setLat(e.target.value)} className="w-32" />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="asset-lng">Longitude</Label>
              <Input id="asset-lng" type="number" step="any" value={lng} onChange={(e) => setLng(e.target.value)} className="w-32" />
            </div>
            <Button type="button" variant="outline" onClick={setLocation}>
              Set location
            </Button>
          </div>

          <div className="grid gap-1.5 max-w-56">
            <Label>Move to site</Label>
            <Select value={asset.site_id ?? undefined} onValueChange={(v) => v && moveToSite(v)}>
              <SelectTrigger>
                <SelectValue placeholder="Select a site" />
              </SelectTrigger>
              <SelectContent>
                {sites.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {asset.status === "failed" ? (
        <Button type="button" variant="outline" onClick={reprocess} disabled={reprocessing}>
          {reprocessing ? "Reprocessing..." : "Reprocess"}
        </Button>
      ) : null}
    </div>
  );
}
