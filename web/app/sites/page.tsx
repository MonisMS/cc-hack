"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Camera, Crosshair, MapPin } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/page-header";
import { MetaLine, PhotoMosaic } from "@/components/photo-mosaic";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { AssetCard, Site } from "@/lib/types";
import { plural, useAcrossProjects } from "@/lib/workspace";

export default function SitesPage() {
  const { items: sites, error } = useAcrossProjects<Site>((id) => `/api/projects/${id}/sites`);
  const [thumbs, setThumbs] = useState<Record<string, string[]>>({});

  useEffect(() => {
    if (!sites) return;
    Promise.all(
      sites.map((s) =>
        api<{ items: AssetCard[] }>(`/api/assets?project_id=${s.project_id}&site_id=${s.id}&limit=4`)
          .then((r) => [s.id, r.items.map((a) => a.thumb_url)] as const)
          .catch(() => [s.id, [] as string[]] as const),
      ),
    ).then((pairs) => setThumbs(Object.fromEntries(pairs)));
  }, [sites]);

  const photos = sites?.reduce((n, s) => n + s.asset_count, 0) ?? null;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <PageHeader
        title="Sites"
        subtitle="Physical locations. Uploaded photos are assigned to the nearest site automatically from their GPS."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Sites" value={sites ? sites.length : null} sub="across all projects" icon={MapPin} gradient="ocean" />
        <StatCard label="Photos placed" value={photos} sub="auto-assigned by location" icon={Camera} gradient="mint" />
        <StatCard
          label="Best covered"
          value={sites?.length ? Math.max(...sites.map((s) => s.asset_count)) : sites ? "—" : null}
          sub={
            sites?.length
              ? `photos at ${[...sites].sort((a, b) => b.asset_count - a.asset_count)[0].name}`
              : "no sites yet"
          }
          icon={Crosshair}
          gradient="sunset"
        />
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {sites === null && !error ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-64 rounded-2xl" />
          ))}
        </div>
      ) : null}

      {sites?.length === 0 ? (
        <EmptyState>No sites yet. Open a project and click Add site.</EmptyState>
      ) : null}

      {sites && sites.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[...sites]
            .sort((a, b) => b.asset_count - a.asset_count)
            .map((s) => {
              return (
                <Card key={s.id} className="gap-0 py-0">
                  <PhotoMosaic urls={thumbs[s.id] ?? []} layout="strip" />
                  <div className="flex flex-wrap items-end justify-between gap-4 p-5">
                    <div className="space-y-1.5">
                      <p className="type-eyebrow text-muted-foreground">{s.project.name}</p>
                      <h3 className="type-title">{s.name}</h3>
                      <MetaLine
                        items={[
                          plural(s.asset_count, "photo"),
                          `${s.lat.toFixed(3)}, ${s.lng.toFixed(3)}`,
                          `${s.radius_m / 1000} km radius`,
                        ]}
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        nativeButton={false}
                        render={<Link href={`/library?project=${s.project_id}&site=${s.id}`}>Photos</Link>}
                      />
                      <Button size="sm" nativeButton={false} render={<Link href={`/sites/${s.id}/compare`}>Compare</Link>} />
                    </div>
                  </div>
                </Card>
              );
            })}
        </div>
      ) : null}
    </div>
  );
}
