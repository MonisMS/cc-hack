"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { AssetCard as AssetCardType, Comparison, PairSuggestion, Site } from "@/lib/types";

const UNSET = "";

export default function ComparePage() {
  const { id: siteId } = useParams<{ id: string }>();
  const router = useRouter();
  const [site, setSite] = useState<Site | null>(null);
  const [suggestions, setSuggestions] = useState<PairSuggestion[] | null>(null);
  const [readyAssets, setReadyAssets] = useState<AssetCardType[]>([]);
  const [comparisons, setComparisons] = useState<Comparison[] | null>(null);
  const [beforeId, setBeforeId] = useState(UNSET);
  const [afterId, setAfterId] = useState(UNSET);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!siteId) return;
    api<Site>(`/api/sites/${siteId}`, { method: "PATCH", body: "{}" })
      .then((s) => {
        setSite(s);
        return api<{ items: AssetCardType[] }>(
          `/api/assets?project_id=${s.project_id}&site_id=${siteId}&status=ready&limit=60`,
        );
      })
      .then((res) => setReadyAssets(res.items))
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load site"));

    api<{ items: PairSuggestion[] }>(`/api/sites/${siteId}/pair-suggestions`)
      .then((res) => setSuggestions(res.items))
      .catch(() => setSuggestions([]));

    api<{ items: Comparison[] }>(`/api/sites/${siteId}/comparisons`)
      .then((res) => setComparisons(res.items))
      .catch(() => setComparisons([]));
  }, [siteId]);

  function createComparison(before: string, after: string) {
    setSubmitting(true);
    api<{ comparison_id: string }>("/api/comparisons", {
      method: "POST",
      body: JSON.stringify({ site_id: siteId, before_asset_id: before, after_asset_id: after }),
    })
      .then((res) => router.push(`/comparisons/${res.comparison_id}`))
      .catch((err) => {
        toast.error(err instanceof ApiErr ? err.message : "Could not create comparison");
        setSubmitting(false);
      });
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Compare{site ? ` — ${site.name}` : ""}</h1>
        <p className="text-muted-foreground">Pick a before/after pair to build a comparison.</p>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <Card>
        <CardHeader>
          <CardTitle>Suggested pairs</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {suggestions === null ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
            </div>
          ) : null}
          {suggestions && suggestions.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No suggested pairs yet — need two ready photos at least 7 days apart.
            </p>
          ) : null}
          {suggestions?.map((s) => (
            <div
              key={`${s.before.id}-${s.after.id}`}
              className="flex flex-wrap items-center gap-4 rounded-md border p-3"
            >
              <div className="flex items-center gap-3">
                <img src={s.before.thumb_url} alt="" className="size-16 rounded object-cover" />
                <span className="text-muted-foreground">→</span>
                <img src={s.after.thumb_url} alt="" className="size-16 rounded object-cover" />
              </div>
              <div className="flex flex-1 flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="secondary">{Math.round(s.image_similarity * 100)}% similar</Badge>
                <span>{s.days_apart} days apart</span>
                {s.framing_warning ? <Badge variant="destructive">framing differs</Badge> : null}
              </div>
              <Button
                type="button"
                disabled={submitting}
                onClick={() => createComparison(s.before.id, s.after.id)}
              >
                Use this pair
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Manual pick</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="grid gap-1.5">
            <span className="text-xs font-medium text-muted-foreground">Before</span>
            <Select value={beforeId} onValueChange={(v) => setBeforeId(v ?? UNSET)}>
              <SelectTrigger className="w-56">
                <SelectValue>
                  {() => readyAssets.find((a) => a.id === beforeId)?.captured_at ?? "Select photo"}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {readyAssets.map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.captured_at ?? a.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <span className="text-xs font-medium text-muted-foreground">After</span>
            <Select value={afterId} onValueChange={(v) => setAfterId(v ?? UNSET)}>
              <SelectTrigger className="w-56">
                <SelectValue>
                  {() => readyAssets.find((a) => a.id === afterId)?.captured_at ?? "Select photo"}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {readyAssets.map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.captured_at ?? a.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            type="button"
            disabled={!beforeId || !afterId || beforeId === afterId || submitting}
            onClick={() => createComparison(beforeId, afterId)}
          >
            {submitting ? "Creating..." : "Create comparison"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Existing comparisons</CardTitle>
        </CardHeader>
        <CardContent>
          {comparisons && comparisons.length === 0 ? (
            <p className="text-sm text-muted-foreground">None yet.</p>
          ) : null}
          {comparisons && comparisons.length > 0 ? (
            <ul className="divide-y">
              {comparisons.map((c) => (
                <li key={c.id} className="flex items-center justify-between py-2">
                  <Link href={`/comparisons/${c.id}`} className="flex items-center gap-3 text-sm hover:underline">
                    <img src={c.before.thumb_url} alt="" className="size-10 rounded object-cover" />
                    <img src={c.after.thumb_url} alt="" className="size-10 rounded object-cover" />
                    <span>
                      {c.before.captured_at ?? "?"} → {c.after.captured_at ?? "?"}
                    </span>
                  </Link>
                  <StatusBadge status={c.status} />
                </li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
