import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { MetaLine, PhotoMosaic } from "@/components/photo-mosaic";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { AssetCard, Project } from "@/lib/types";
import { plural } from "@/lib/workspace";

export type ProjectExtras = { thumbs: string[]; comparisons: number; reports: number };

export function loadProjectExtras(p: Project): Promise<ProjectExtras> {
  return Promise.all([
    api<{ items: AssetCard[] }>(`/api/assets?project_id=${p.id}&limit=3`),
    api<{ items: unknown[] }>(`/api/projects/${p.id}/comparisons`),
    api<{ items: unknown[] }>(`/api/projects/${p.id}/reports`),
  ]).then(([assets, comparisons, reports]) => ({
    thumbs: assets.items.map((a) => a.thumb_url).filter(Boolean),
    comparisons: comparisons.items.length,
    reports: reports.items.length,
  }));
}

export function ProjectCard({ project: p, extras: x }: { project: Project; extras?: ProjectExtras }) {
  const pending = p.asset_count - p.ready_count - p.failed_count;
  return (
    <Link href={`/projects/${p.id}`} className="group">
      <Card className="h-full gap-0 py-0 transition-all group-hover:-translate-y-0.5 group-hover:shadow-[0_18px_40px_-18px_rgb(60_45_160/0.28)]">
        <PhotoMosaic urls={x?.thumbs ?? []} />
        <div className="flex flex-1 flex-col gap-3 p-5">
          <div className="space-y-1">
            <p className="type-eyebrow text-muted-foreground">
              Project{p.started_on ? ` · since ${p.started_on.slice(0, 7)}` : ""}
            </p>
            <div className="flex items-center justify-between gap-3">
              <h3 className="type-title">{p.name}</h3>
              <ArrowUpRight className="size-5 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
            </div>
            {p.description ? <p className="line-clamp-2 text-sm text-muted-foreground">{p.description}</p> : null}
          </div>
          <MetaLine
            className="mt-auto"
            items={[
              plural(p.site_count, "site"),
              plural(p.asset_count, "photo"),
              x ? plural(x.comparisons, "comparison") : null,
              x ? plural(x.reports, "report") : null,
            ]}
          />
          <p className="flex items-center gap-2 text-xs font-medium">
            <span className={pending > 0 ? "size-2 rounded-full bg-amber-500" : "size-2 rounded-full bg-emerald-500"} />
            {pending > 0 ? `${pending} photos being analysed` : "All photos analysed"}
            {p.failed_count > 0 ? <span className="text-destructive"> · {p.failed_count} failed</span> : null}
          </p>
        </div>
      </Card>
    </Link>
  );
}
