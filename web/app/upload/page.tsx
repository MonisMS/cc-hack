"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, BrainCircuit, CalendarClock, MapPin, ShieldCheck, Upload } from "lucide-react";
import { NewProjectDialog } from "@/components/new-project-dialog";
import { EmptyState, PageHeader } from "@/components/page-header";
import { MetaLine } from "@/components/photo-mosaic";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { Project } from "@/lib/types";
import { plural } from "@/lib/workspace";

const AFTER_UPLOAD = [
  { icon: ShieldCheck, title: "Consent checked", text: "Upload only starts after the uploader confirms consent." },
  { icon: CalendarClock, title: "Date read", text: "Capture date comes from the photo's EXIF data." },
  { icon: MapPin, title: "Placed on a site", text: "GPS (or your device location) assigns it to the nearest site." },
  { icon: BrainCircuit, title: "Tagged by AI", text: "CLIP and Cloudinary detection tag what's in it, and it becomes searchable." },
];

export default function UploadPickerPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<{ items: Project[] }>("/api/projects")
      .then((res) => setProjects(res.items))
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load projects"));
  }, []);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <PageHeader
        title="Upload"
        subtitle="Choose which project the new field photos belong to."
        action={<NewProjectDialog onCreated={(project) => setProjects((prev) => [project, ...(prev ?? [])])} />}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {AFTER_UPLOAD.map(({ icon: Icon, title, text }, i) => (
          <div key={title} className="flex gap-3 rounded-2xl bg-card p-4 ring-1 ring-foreground/[0.04]">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-secondary text-secondary-foreground">
              <Icon className="size-[18px]" />
            </span>
            <div>
              <p className="text-sm font-medium">
                {i + 1}. {title}
              </p>
              <p className="text-xs text-muted-foreground">{text}</p>
            </div>
          </div>
        ))}
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {projects === null && !error ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-28 rounded-2xl" />
          ))}
        </div>
      ) : null}

      {projects?.length === 0 ? <EmptyState>No projects yet. Create one first, then upload into it.</EmptyState> : null}

      {projects && projects.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {projects.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}/upload`} className="group">
              <Card className="h-full flex-row items-center gap-4 px-5 transition-all group-hover:-translate-y-0.5 group-hover:shadow-[0_18px_40px_-18px_rgb(60_45_160/0.28)]">
                <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-[0_6px_16px_-6px_var(--primary)]">
                  <Upload className="size-5" />
                </span>
                <div className="min-w-0 flex-1 space-y-1">
                  <h3 className="type-title truncate">{p.name}</h3>
                  <MetaLine items={[plural(p.site_count, "site"), `${plural(p.asset_count, "photo")} so far`]} />
                </div>
                <ArrowRight className="size-5 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
              </Card>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
