"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Activity, ArrowLeftRight, Camera, MapPin } from "lucide-react";
import { AssetGrid } from "@/components/asset-grid";
import { LineagePanel } from "@/components/lineage-panel";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr, usePoll } from "@/lib/api";
import type { KitItem, Report } from "@/lib/types";

function isDone(r: Report) {
  return r.status === "ready" || r.status === "failed";
}

const KIT_LABEL: Record<KitItem["kind"], string> = {
  social_square: "Social square",
  social_story: "Social story",
  collage: "Before/after collage",
};

function CampaignKit({ reportId }: { reportId: string }) {
  const [items, setItems] = useState<KitItem[] | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);

  useEffect(() => {
    api<{ items: KitItem[] }>(`/api/reports/${reportId}/campaign-kit`)
      .then((res) => setItems(res.items))
      .catch((err) =>
        setError(
          err instanceof ApiErr
            ? { code: err.code, message: err.message }
            : { code: "UNKNOWN", message: "Could not load campaign kit" },
        ),
      );
  }, [reportId]);

  if (error?.code === "CREDIT_GUARD") {
    return (
      <p className="text-sm text-muted-foreground">
        Campaign kit is paused for now — the Cloudinary usage guard tripped. Try again later.
      </p>
    );
  }
  if (error) return <p className="text-sm text-destructive">{error.message}</p>;
  if (items === null) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="aspect-square" />
        ))}
      </div>
    );
  }
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">No kit items — this report has no evidence yet.</p>;
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
      {items.map((item, i) => (
        <div key={`${item.kind}-${i}`} className="space-y-2 rounded-md border p-2">
          <img src={item.url} alt={KIT_LABEL[item.kind]} className="aspect-square w-full rounded object-cover" />
          <p className="text-xs font-medium">{KIT_LABEL[item.kind]}</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => window.open(item.url, "_blank")}>
              Download
            </Button>
            <LineagePanel
              entityType="kit"
              entityId={reportId}
              trigger={
                <Button variant="ghost" size="sm">
                  Lineage
                </Button>
              }
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const { data: report, error } = usePoll<Report>(id ? `/api/reports/${id}` : null, isDone);

  if (error) {
    return <p className="p-8 text-sm text-destructive">{error.message}</p>;
  }

  if (!report) {
    return (
      <div className="p-8 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32" />
      </div>
    );
  }

  if (report.status === "pending" || report.status === "processing") {
    return (
      <div className="p-8 space-y-4">
        <h1 className="type-display">Generating report...</h1>
        <Skeleton className="h-32" />
      </div>
    );
  }

  if (report.status === "failed") {
    return (
      <div className="p-8 space-y-2">
        <h1 className="type-display">Report failed</h1>
        <p className="text-sm text-muted-foreground">Something went wrong generating this report.</p>
      </div>
    );
  }

  const metrics = report.metrics as {
    assets_total?: number;
    images?: number;
    videos?: number;
    sites_with_evidence?: number;
    first_capture?: string | null;
    last_capture?: string | null;
    top_activities?: { tag: string; count: number }[];
  };

  const activityItems = report.items.filter((i) => i.kind === "asset" && i.section === "activities");
  const beforeAfterItems = report.items.filter((i) => i.kind === "comparison" && i.section === "before_after");

  return (
    <div className="p-8 space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="type-display">{report.summary?.headline ?? "Report"}</h1>
          <p className="text-muted-foreground">
            {report.date_from} → {report.date_to}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            nativeButton={false}
            render={<Link href={`/reports/${report.id}/print`}>Print / PDF</Link>}
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Photos analysed" value={metrics.images ?? 0} sub={`${metrics.assets_total ?? 0} assets in range`} icon={Camera} gradient="sunset" />
        <StatCard label="Sites with evidence" value={metrics.sites_with_evidence ?? 0} sub={metrics.first_capture ? `${metrics.first_capture} → ${metrics.last_capture}` : undefined} icon={MapPin} gradient="ocean" />
        <StatCard label="Before / after comparisons" value={beforeAfterItems.length} sub="estimated green-cover change" icon={ArrowLeftRight} gradient="mint" />
        <StatCard
          label="Top activity"
          value={metrics.top_activities?.[0]?.count ?? 0}
          sub={metrics.top_activities?.[0] ? `photos tagged ${metrics.top_activities[0].tag.replace(/_/g, " ")}` : "no tagged activity"}
          icon={Activity}
          gradient="lilac"
        />
      </div>

      {report.summary ? (
        <Card>
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-[15px] leading-relaxed">
            {report.summary.paragraphs.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {report.summary.highlights.map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">model: {report.summary_model ?? "template"}</p>
          </CardContent>
        </Card>
      ) : null}

      {beforeAfterItems.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Before / after</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {beforeAfterItems.map((item) =>
              item.comparison ? (
                <Link
                  key={item.comparison.id}
                  href={`/comparisons/${item.comparison.id}`}
                  className="flex flex-wrap items-center gap-4 rounded-md border p-3 hover:border-primary/50"
                >
                  <img src={item.comparison.before_compare_url} alt="Before" className="h-24 w-32 rounded object-cover" />
                  <img src={item.comparison.after_compare_url} alt="After" className="h-24 w-32 rounded object-cover" />
                  <div className="text-sm">
                    <p className="font-medium">{item.comparison.site_name}</p>
                    <p className="text-muted-foreground">
                      {item.comparison.before_green_pct_rounded}% → {item.comparison.after_green_pct_rounded}%
                      {item.comparison.delta_green_pct_rounded != null
                        ? ` (${item.comparison.delta_green_pct_rounded > 0 ? "+" : ""}${item.comparison.delta_green_pct_rounded} pts)`
                        : ""}
                    </p>
                  </div>
                </Link>
              ) : null,
            )}
          </CardContent>
        </Card>
      ) : null}

      {activityItems.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Evidence by activity</CardTitle>
          </CardHeader>
          <CardContent>
            <AssetGrid assets={activityItems.map((i) => i.asset!).filter(Boolean)} />
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Campaign kit</CardTitle>
        </CardHeader>
        <CardContent>
          <CampaignKit reportId={report.id} />
        </CardContent>
      </Card>
    </div>
  );
}
