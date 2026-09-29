"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ReactCompareSlider, ReactCompareSliderImage } from "react-compare-slider";
import { ArrowUpRight } from "lucide-react";
import { AssetCard } from "@/components/asset-card";
import { ColumnChart, HBarList, type Datum } from "@/components/bar-charts";
import { GreenDelta } from "@/components/green-delta";
import { MetaLine } from "@/components/photo-mosaic";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { AssetCard as AssetCardType, Comparison, KitItem, KitItemKind, Project, Report, Site } from "@/lib/types";
import { plural } from "@/lib/workspace";

type Insights = {
  assets: AssetCardType[];
  comparisons: Comparison[];
  sites: Site[];
  report: Report | null;
  kit: KitItem[];
};

async function allAssets(projectId: string): Promise<AssetCardType[]> {
  const out: AssetCardType[] = [];
  let cursor: string | null = null;
  do {
    const q = new URLSearchParams({ project_id: projectId, limit: "60" });
    if (cursor) q.set("cursor", cursor);
    const page: { items: AssetCardType[]; next_cursor: string | null } = await api(`/api/assets?${q}`);
    out.push(...page.items);
    cursor = page.next_cursor;
  } while (cursor && out.length < 600);
  return out;
}

async function loadInsights(p: Project): Promise<Insights> {
  const [assets, comparisons, sites, reports] = await Promise.all([
    allAssets(p.id),
    api<{ items: Comparison[] }>(`/api/projects/${p.id}/comparisons`).then((r) => r.items),
    api<{ items: Site[] }>(`/api/projects/${p.id}/sites`).then((r) => r.items),
    api<{ items: Report[] }>(`/api/projects/${p.id}/reports`).then((r) => r.items),
  ]);
  const report = reports.find((r) => r.status === "ready") ?? null;
  const kit = report
    ? await api<{ items: KitItem[] }>(`/api/reports/${report.id}/campaign-kit`).then((r) => r.items).catch(() => [])
    : [];
  return { assets, comparisons, sites, report, kit };
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

function photosPerMonth(assets: AssetCardType[]): Datum[] {
  const keys = assets.map((a) => a.captured_at?.slice(0, 7)).filter(Boolean) as string[];
  if (keys.length === 0) return [];
  const counts = keys.reduce<Record<string, number>>((acc, k) => ((acc[k] = (acc[k] ?? 0) + 1), acc), {});
  const sorted = Object.keys(counts).sort();
  const out: Datum[] = [];
  let [y, m] = sorted[0].split("-").map(Number);
  const [ey, em] = sorted[sorted.length - 1].split("-").map(Number);
  while (y < ey || (y === ey && m <= em)) {
    const key = `${y}-${String(m).padStart(2, "0")}`;
    out.push({ label: `${MONTHS[m - 1]} ${y}`, value: counts[key] ?? 0 });
    m += 1;
    if (m > 12) {
      m = 1;
      y += 1;
    }
  }
  return out;
}

function topTags(assets: AssetCardType[], n = 8): Datum[] {
  const counts = assets.reduce<Record<string, number>>((acc, a) => {
    // A tag can come from both CLIP and object detection; count each photo once per tag.
    for (const tag of new Set(a.tags.map((t) => t.tag))) acc[tag] = (acc[tag] ?? 0) + 1;
    return acc;
  }, {});
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([tag, value]) => ({ label: tag.replace(/_/g, " "), value }));
}

function SectionCard({
  eyebrow,
  title,
  action,
  children,
  className,
}: {
  eyebrow: string;
  title: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="type-eyebrow text-primary">{eyebrow}</p>
          <CardTitle className="text-lg">{title}</CardTitle>
        </div>
        {action}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

const KIT_LABEL: Record<KitItemKind, string> = {
  collage: "Before/after collage",
  social_square: "Social square",
  social_story: "Story",
};

export function DashboardInsights({ project }: { project: Project }) {
  const [data, setData] = useState<Insights | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    loadInsights(project)
      .then(setData)
      .catch(() => setFailed(true));
  }, [project]);

  if (failed) return null;
  if (!data) {
    return (
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-96 rounded-2xl lg:col-span-2" />
        <Skeleton className="h-96 rounded-2xl" />
      </div>
    );
  }

  const ready = data.comparisons.filter((c) => c.status === "ready");
  const featured = ready.length
    ? ready.reduce((best, c) => ((c.delta_green_pct_rounded ?? -Infinity) > (best.delta_green_pct_rounded ?? -Infinity) ? c : best))
    : null;
  const latestBySite = new Map<string, Comparison>();
  for (const c of ready) if (!latestBySite.has(c.site_id)) latestBySite.set(c.site_id, c); // list is newest first
  const sites = [...data.sites].sort((a, b) => b.asset_count - a.asset_count);
  const months = photosPerMonth(data.assets);
  const tags = topTags(data.assets);
  const kit = (["collage", "social_square", "social_story"] as const)
    .map((kind) => data.kit.find((k) => k.kind === kind))
    .filter(Boolean) as KitItem[];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-3">
        {featured ? (
          <SectionCard
            className="lg:col-span-2"
            eyebrow="Featured before / after"
            title={featured.site_name}
            action={<GreenDelta value={featured.delta_green_pct_rounded} />}
          >
            <div className="overflow-hidden rounded-xl">
              <ReactCompareSlider
                itemOne={<ReactCompareSliderImage src={featured.before_compare_url} alt="Before" />}
                itemTwo={<ReactCompareSliderImage src={featured.after_compare_url} alt="After" />}
                className="aspect-video"
              />
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <MetaLine
                items={[
                  featured.before_green_pct_rounded != null
                    ? `Green cover ${featured.before_green_pct_rounded}% → ${featured.after_green_pct_rounded}%`
                    : null,
                  featured.days_apart != null ? `${featured.days_apart} days apart` : null,
                  "drag to compare",
                ]}
              />
              <Button size="sm" variant="outline" nativeButton={false} render={<Link href={`/comparisons/${featured.id}`}>Open comparison</Link>} />
            </div>
          </SectionCard>
        ) : null}

        <SectionCard
          eyebrow="Sites"
          title="Site leaderboard"
          className={featured ? "[&>[data-slot=card-content]]:flex [&>[data-slot=card-content]]:flex-1 [&>[data-slot=card-content]]:flex-col" : "lg:col-span-3"}
          action={
            <Link href="/sites" className="text-sm font-medium text-primary hover:underline">
              All sites
            </Link>
          }
        >
          <ol className="divide-y">
            {sites.map((s, i) => {
              const c = latestBySite.get(s.id);
              return (
                <li key={s.id}>
                  <Link href={`/sites/${s.id}/compare`} className="group flex items-center gap-3 py-3">
                    <span className="grid size-8 shrink-0 place-items-center rounded-full bg-secondary text-xs font-bold text-secondary-foreground">
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold group-hover:text-primary">{s.name}</p>
                      <p className="text-xs text-muted-foreground">{plural(s.asset_count, "photo")}</p>
                    </div>
                    {c ? <GreenDelta value={c.delta_green_pct_rounded} /> : <span className="text-xs text-muted-foreground">no comparison</span>}
                  </Link>
                </li>
              );
            })}
          </ol>
          <div className="mt-auto space-y-3 rounded-xl bg-muted/60 p-4">
            <p className="text-sm">
              <span className="font-semibold">{plural(data.assets.filter((a) => !a.site_id).length, "photo")}</span>
              <span className="text-muted-foreground"> not yet placed on a site</span>
            </p>
            <Button size="sm" className="w-full" nativeButton={false} render={<Link href="/sites">Build a comparison</Link>} />
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {tags.length ? (
          <SectionCard eyebrow="AI tagging" title="What the AI sees in your photos">
            <HBarList data={tags} unit="photos" labelHeader="Tag" />
          </SectionCard>
        ) : null}
        {months.length ? (
          <SectionCard eyebrow="Collection" title="Evidence over time">
            <ColumnChart data={months} unit="photos" labelHeader="Month" />
            <p className="mt-3 text-xs text-muted-foreground">Photos per month, by capture date.</p>
          </SectionCard>
        ) : null}
      </div>

      {data.report ? (
        <Card className="gap-0 py-0">
          <div className="grid lg:grid-cols-[1fr_auto]">
            <div className="flex flex-col justify-between gap-5 p-6">
              <div className="space-y-2">
                <p className="type-eyebrow text-primary">Latest report</p>
                <h3 className="type-title text-xl">{data.report.summary?.headline ?? "Report"}</h3>
                <MetaLine
                  items={[
                    `${data.report.date_from ?? "?"} → ${data.report.date_to ?? "?"}`,
                    plural(data.report.items.filter((i) => i.kind === "comparison").length, "comparison"),
                    plural(data.report.items.filter((i) => i.kind === "asset").length, "evidence photo"),
                  ]}
                />
                {data.report.summary?.paragraphs[0] ? (
                  <p className="line-clamp-3 max-w-xl text-sm text-muted-foreground">{data.report.summary.paragraphs[0]}</p>
                ) : null}
              </div>
              <div className="flex gap-2">
                <Button nativeButton={false} render={<Link href={`/reports/${data.report.id}`}>Open report</Link>} />
                <Button variant="outline" nativeButton={false} render={<Link href={`/reports/${data.report.id}/print`}>Print / PDF</Link>} />
              </div>
            </div>
            {kit.length ? (
              <div className="flex items-end gap-3 overflow-x-auto bg-muted/60 p-5">
                {kit.map((k) => (
                  <a key={k.kind} href={k.url} target="_blank" rel="noreferrer" className="group shrink-0 space-y-1.5">
                    <img
                      src={k.url}
                      alt={KIT_LABEL[k.kind]}
                      loading="lazy"
                      className={
                        k.kind === "collage"
                          ? "h-36 w-72 rounded-xl object-cover shadow-sm transition-transform group-hover:-translate-y-0.5"
                          : k.kind === "social_square"
                            ? "size-36 rounded-xl object-cover shadow-sm transition-transform group-hover:-translate-y-0.5"
                            : "h-44 w-[6.2rem] rounded-xl object-cover shadow-sm transition-transform group-hover:-translate-y-0.5"
                      }
                    />
                    <p className="text-[11px] font-medium text-muted-foreground">{KIT_LABEL[k.kind]}</p>
                  </a>
                ))}
              </div>
            ) : null}
          </div>
        </Card>
      ) : null}

      {data.assets.length ? (
        <section className="space-y-3">
          <div className="flex items-end justify-between gap-3">
            <div className="space-y-1">
              <p className="type-eyebrow text-primary">Library</p>
              <h2 className="type-title">Recent uploads</h2>
            </div>
            <Link href="/library" className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
              View all <ArrowUpRight className="size-4" />
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {data.assets.slice(0, 6).map((a) => (
              <AssetCard key={a.id} asset={a} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
