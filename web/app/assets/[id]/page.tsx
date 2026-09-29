"use client";

import { XIcon } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { LineagePanel } from "@/components/lineage-panel";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { AssetDetail, Site, Tag } from "@/lib/types";

const TAG_VARIANT: Record<Tag["source"], "secondary" | "outline" | "default"> = {
  clip: "secondary",
  cld_detection: "outline",
  manual: "default",
};

function TagGroup({
  title,
  tags,
  removable,
  onRemove,
}: {
  title: string;
  tags: Tag[];
  removable?: boolean;
  onRemove?: (tag: string) => void;
}) {
  if (tags.length === 0) return null;
  return (
    <div className="space-y-1.5">
      <span className="text-xs font-medium text-muted-foreground">{title}</span>
      <div className="flex flex-wrap gap-1.5">
        {tags.map((t) => (
          <Badge key={`${t.source}-${t.tag}`} variant={TAG_VARIANT[t.source]} className="gap-1">
            {t.tag}
            {removable ? (
              <button
                type="button"
                onClick={() => onRemove?.(t.tag)}
                className="ml-0.5 rounded-full hover:bg-background/50"
              >
                <XIcon className="size-3" />
              </button>
            ) : null}
          </Badge>
        ))}
      </div>
    </div>
  );
}

export default function AssetDetailPage() {
  const { id: assetId } = useParams<{ id: string }>();
  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newTag, setNewTag] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [reprocessing, setReprocessing] = useState(false);

  async function refetch() {
    try {
      const a = await api<AssetDetail>(`/api/assets/${assetId}`);
      setAsset(a);
      if (a.lat_r != null) setLat(String(a.lat_r));
      if (a.lng_r != null) setLng(String(a.lng_r));
      return a;
    } catch (err) {
      setError(err instanceof ApiErr ? err.message : "Could not load asset");
      return null;
    }
  }

  useEffect(() => {
    if (!assetId) return;
    api<AssetDetail>(`/api/assets/${assetId}`)
      .then((a) => {
        setAsset(a);
        if (a.lat_r != null) setLat(String(a.lat_r));
        if (a.lng_r != null) setLng(String(a.lng_r));
      })
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load asset"));
  }, [assetId]);

  useEffect(() => {
    if (!asset) return;
    api<{ items: Site[] }>(`/api/projects/${asset.project_id}/sites`)
      .then((res) => setSites(res.items))
      .catch(() => {});
  }, [asset?.project_id]); // eslint-disable-line react-hooks/exhaustive-deps

  // poll while reprocessing / pending
  useEffect(() => {
    if (!asset || (asset.status !== "pending" && asset.status !== "processing")) return;
    const timer = setTimeout(refetch, 2000);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asset]);

  async function patch(body: Record<string, unknown>) {
    try {
      const updated = await api<AssetDetail>(`/api/assets/${assetId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setAsset(updated);
      toast.success("Saved");
    } catch (err) {
      toast.error(err instanceof ApiErr ? err.message : "Could not save");
    }
  }

  async function handleReprocess() {
    setReprocessing(true);
    try {
      await api(`/api/assets/${assetId}/reprocess`, { method: "POST" });
      toast.success("Reprocessing...");
      await refetch();
    } catch (err) {
      toast.error(err instanceof ApiErr ? err.message : "Could not reprocess");
    } finally {
      setReprocessing(false);
    }
  }

  if (error) return <p className="p-8 text-sm text-destructive">{error}</p>;

  if (!asset) {
    return (
      <div className="p-8 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  const clipTags = asset.tags.filter((t) => t.source === "clip");
  const detectionTags = asset.tags.filter((t) => t.source === "cld_detection");
  const manualTags = asset.tags.filter((t) => t.source === "manual");

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{asset.site_name ?? "Unassigned asset"}</h1>
          <div className="mt-1 flex items-center gap-2">
            <StatusBadge status={asset.status} />
            {asset.error ? <span className="text-xs text-destructive">{asset.error}</span> : null}
          </div>
        </div>
        <div className="flex gap-2">
          {asset.status === "failed" ? (
            <Button variant="outline" onClick={handleReprocess} disabled={reprocessing}>
              {reprocessing ? "Reprocessing..." : "Reprocess"}
            </Button>
          ) : null}
          <LineagePanel entityType="asset" entityId={asset.id} />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <img
          src={asset.compare_url}
          alt=""
          className="w-full rounded-lg border object-contain bg-muted"
        />

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Tags</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <TagGroup title="CLIP" tags={clipTags} />
              <TagGroup title="Detection" tags={detectionTags} />
              <TagGroup
                title="Manual"
                tags={manualTags}
                removable
                onRemove={(tag) => patch({ remove_tags: [tag] })}
              />
              <form
                className="flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  const t = newTag.trim().toLowerCase();
                  if (!t) return;
                  patch({ add_tags: [t] });
                  setNewTag("");
                }}
              >
                <Input
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  placeholder="Add a tag"
                  className="h-8"
                />
                <Button type="submit" size="sm" variant="outline">
                  Add
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Capture info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div>
                <span className="text-muted-foreground">Date: </span>
                {asset.captured_at ? new Date(asset.captured_at).toLocaleString() : "Unknown"}
                {asset.captured_at_source ? (
                  <span className="ml-1 text-xs text-muted-foreground">({asset.captured_at_source})</span>
                ) : null}
              </div>
              <div>
                <span className="text-muted-foreground">Location: </span>
                {asset.lat_r != null && asset.lng_r != null ? `${asset.lat_r}, ${asset.lng_r}` : "Unknown"}
                {asset.location_source ? (
                  <span className="ml-1 text-xs text-muted-foreground">({asset.location_source})</span>
                ) : null}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Set location</CardTitle>
            </CardHeader>
            <CardContent>
              <form
                className="space-y-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  const latNum = Number(lat);
                  const lngNum = Number(lng);
                  if (Number.isNaN(latNum) || Number.isNaN(lngNum)) return;
                  patch({ lat: latNum, lng: lngNum });
                }}
              >
                <div className="grid grid-cols-2 gap-2">
                  <div className="grid gap-1">
                    <Label htmlFor="asset-lat" className="text-xs">
                      Latitude
                    </Label>
                    <Input id="asset-lat" value={lat} onChange={(e) => setLat(e.target.value)} />
                  </div>
                  <div className="grid gap-1">
                    <Label htmlFor="asset-lng" className="text-xs">
                      Longitude
                    </Label>
                    <Input id="asset-lng" value={lng} onChange={(e) => setLng(e.target.value)} />
                  </div>
                </div>
                <Button type="submit" size="sm" variant="outline">
                  Update location
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Move to site</CardTitle>
            </CardHeader>
            <CardContent>
              <Select
                value={asset.site_id ?? undefined}
                onValueChange={(siteId) => patch({ site_id: siteId })}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a site">
                    {() => sites.find((s) => s.id === asset.site_id)?.name ?? "Select a site"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {sites.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
