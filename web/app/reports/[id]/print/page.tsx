"use client";

import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { usePoll } from "@/lib/api";
import type { Report } from "@/lib/types";

function isDone(r: Report) {
  return r.status === "ready" || r.status === "failed";
}

export default function ReportPrintPage() {
  const { id } = useParams<{ id: string }>();
  const { data: report, error } = usePoll<Report>(id ? `/api/reports/${id}` : null, isDone);

  if (error) {
    return <p className="p-8 text-sm text-destructive">{error.message}</p>;
  }

  if (!report || report.status !== "ready") {
    return (
      <div className="mx-auto max-w-2xl space-y-4 p-8">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32" />
      </div>
    );
  }

  const metrics = report.metrics as {
    assets_total?: number;
    images?: number;
    sites_with_evidence?: number;
    first_capture?: string | null;
    last_capture?: string | null;
  };

  const activityItems = report.items.filter((i) => i.kind === "asset" && i.section === "activities");
  const beforeAfterItems = report.items.filter((i) => i.kind === "comparison" && i.section === "before_after");

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-8 print:max-w-none">
      <div className="no-print">
        <Button onClick={() => window.print()}>Print / Save as PDF</Button>
      </div>

      <div className="print-card space-y-1 border-b pb-4">
        <h1 className="type-display">{report.summary?.headline ?? "Field report"}</h1>
        <p className="text-sm text-muted-foreground">
          {report.date_from} → {report.date_to}
        </p>
      </div>

      {report.summary ? (
        <div className="print-card space-y-3">
          {report.summary.paragraphs.map((p, i) => (
            <p key={i} className="text-sm">
              {p}
            </p>
          ))}
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {report.summary.highlights.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="print-card grid grid-cols-4 gap-2 border-y py-3 text-center text-xs">
        <div>
          <p className="text-lg font-semibold">{metrics.assets_total ?? 0}</p>
          <p className="text-muted-foreground">assets</p>
        </div>
        <div>
          <p className="text-lg font-semibold">{metrics.images ?? 0}</p>
          <p className="text-muted-foreground">photos</p>
        </div>
        <div>
          <p className="text-lg font-semibold">{metrics.sites_with_evidence ?? 0}</p>
          <p className="text-muted-foreground">sites</p>
        </div>
        <div>
          <p className="text-sm font-medium">
            {metrics.first_capture ?? "—"} → {metrics.last_capture ?? "—"}
          </p>
          <p className="text-muted-foreground">span</p>
        </div>
      </div>

      {beforeAfterItems.length > 0 ? (
        <div className="print-card space-y-3">
          <h2 className="text-lg font-semibold">Before / after</h2>
          {beforeAfterItems.map((item) =>
            item.comparison ? (
              <div key={item.comparison.id} className="print-card flex items-center gap-3 border rounded-md p-2">
                <img src={item.comparison.before_compare_url} alt="Before" className="h-20 w-28 rounded object-cover" />
                <img src={item.comparison.after_compare_url} alt="After" className="h-20 w-28 rounded object-cover" />
                <div className="text-sm">
                  <p className="font-medium">{item.comparison.site_name}</p>
                  <p className="text-muted-foreground">
                    {item.comparison.before_green_pct_rounded}% → {item.comparison.after_green_pct_rounded}%
                  </p>
                  {item.comparison.description ? <p className="text-xs mt-1">{item.comparison.description}</p> : null}
                </div>
              </div>
            ) : null,
          )}
        </div>
      ) : null}

      {activityItems.length > 0 ? (
        <div className="print-card space-y-3">
          <h2 className="text-lg font-semibold">Evidence</h2>
          <div className="grid grid-cols-4 gap-2">
            {activityItems.map((item) =>
              item.asset ? (
                <img
                  key={item.asset.id}
                  src={item.asset.thumb_url}
                  alt=""
                  className="aspect-4/3 w-full rounded object-cover"
                />
              ) : null,
            )}
          </div>
        </div>
      ) : null}

      <p className="text-xs text-muted-foreground border-t pt-3">
        Green cover figures are estimates from a simple color-threshold algorithm, not a scientific survey.
      </p>
    </div>
  );
}
