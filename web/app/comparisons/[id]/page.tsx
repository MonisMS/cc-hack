"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { ReactCompareSlider, ReactCompareSliderImage } from "react-compare-slider";
import { LineagePanel } from "@/components/lineage-panel";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { usePoll } from "@/lib/api";
import type { Comparison } from "@/lib/types";

function isDone(c: Comparison) {
  return c.status === "ready" || c.status === "failed";
}

export default function ComparisonPage() {
  const { id } = useParams<{ id: string }>();
  const [showMask, setShowMask] = useState(false);
  const { data: comparison, error } = usePoll<Comparison>(
    id ? `/api/comparisons/${id}` : null,
    isDone,
  );

  if (error) {
    return <p className="p-8 text-sm text-destructive">{error.message}</p>;
  }

  if (!comparison) {
    return (
      <div className="p-8 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="aspect-video" />
      </div>
    );
  }

  if (comparison.status === "pending" || comparison.status === "processing") {
    return (
      <div className="p-8 space-y-4">
        <h1 className="text-2xl font-semibold">Building comparison...</h1>
        <StatusBadge status={comparison.status} />
        <Skeleton className="aspect-video" />
      </div>
    );
  }

  if (comparison.status === "failed") {
    return (
      <div className="p-8 space-y-2">
        <h1 className="text-2xl font-semibold">Comparison failed</h1>
        <p className="text-sm text-muted-foreground">Something went wrong building this comparison.</p>
      </div>
    );
  }

  const canShowMask = comparison.before_mask_url && comparison.after_mask_url;
  const beforeSrc = showMask && canShowMask ? comparison.before_mask_url! : comparison.before_compare_url;
  const afterSrc = showMask && canShowMask ? comparison.after_mask_url! : comparison.after_compare_url;

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{comparison.site_name}</h1>
          <p className="text-muted-foreground">
            {comparison.days_apart} days apart
            {comparison.framing_warning ? " · framing differs from before to after" : ""}
          </p>
        </div>
        <LineagePanel entityType="comparison" entityId={comparison.id} />
      </div>

      {comparison.framing_warning ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          ⚠️ The before and after photos were taken from noticeably different angles — treat the estimate with
          caution.
        </div>
      ) : null}

      <div className="overflow-hidden rounded-lg border">
        <ReactCompareSlider
          itemOne={<ReactCompareSliderImage src={beforeSrc} alt="Before" />}
          itemTwo={<ReactCompareSliderImage src={afterSrc} alt="After" />}
        />
      </div>

      {canShowMask ? (
        <Button type="button" variant="outline" onClick={() => setShowMask((v) => !v)}>
          {showMask ? "Hide green mask" : "Show green mask"}
        </Button>
      ) : null}

      <div className="rounded-lg border p-4">
        <p className="text-lg font-semibold">
          Estimated green cover: {comparison.before_green_pct_rounded ?? "—"}% → {comparison.after_green_pct_rounded ?? "—"}%
          {comparison.delta_green_pct_rounded != null ? (
            <span className="ml-2 text-muted-foreground">
              ({comparison.delta_green_pct_rounded > 0 ? "+" : ""}
              {comparison.delta_green_pct_rounded} points)
            </span>
          ) : null}
        </p>
      </div>

      {comparison.description ? (
        <div className="space-y-1">
          <p>{comparison.description}</p>
          <p className="text-xs text-muted-foreground">model: {comparison.description_model ?? "template"}</p>
        </div>
      ) : null}

      <div className="flex gap-2">
        <Badge variant="secondary">before: {comparison.before.captured_at?.slice(0, 10) ?? "unknown date"}</Badge>
        <Badge variant="secondary">after: {comparison.after.captured_at?.slice(0, 10) ?? "unknown date"}</Badge>
      </div>
    </div>
  );
}
