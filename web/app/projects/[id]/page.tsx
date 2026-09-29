"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AddSiteDialog } from "@/components/add-site-dialog";
import { NewReportDialog } from "@/components/new-report-dialog";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, ApiErr } from "@/lib/api";
import type { Comparison, Project, Report, Site } from "@/lib/types";

export default function ProjectOverviewPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [sites, setSites] = useState<Site[] | null>(null);
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [reports, setReports] = useState<Report[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api<Project>(`/api/projects/${id}`),
      api<{ items: Site[] }>(`/api/projects/${id}/sites`),
      api<{ items: Comparison[] }>(`/api/projects/${id}/comparisons?status=ready`),
      api<{ items: Report[] }>(`/api/projects/${id}/reports`),
    ])
      .then(([p, s, c, r]) => {
        setProject(p);
        setSites(s.items);
        setComparisons(c.items);
        setReports(r.items);
      })
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load project"));
  }, [id]);

  if (error) {
    return <p className="p-8 text-destructive text-sm">{error}</p>;
  }

  if (!project) {
    return (
      <div className="p-8 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32" />
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="type-display">{project.name}</h1>
        {project.description ? <p className="text-muted-foreground mt-1">{project.description}</p> : null}
        <div className="flex flex-wrap gap-2 mt-3 text-xs">
          <Badge variant="secondary">{project.site_count} sites</Badge>
          <Badge variant="secondary">{project.asset_count} assets</Badge>
          <Badge variant="secondary">{project.ready_count} ready</Badge>
          {project.failed_count > 0 ? <Badge variant="destructive">{project.failed_count} failed</Badge> : null}
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Sites</CardTitle>
          <AddSiteDialog
            projectId={id}
            onCreated={(site) => {
              setSites((prev) => [...(prev ?? []), site]);
              setProject((prev) => (prev ? { ...prev, site_count: prev.site_count + 1 } : prev));
            }}
          />
        </CardHeader>
        <CardContent>
          {sites && sites.length === 0 ? (
            <p className="text-sm text-muted-foreground">No sites yet — add one to start uploading photos there.</p>
          ) : null}
          {sites && sites.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Lat</TableHead>
                  <TableHead>Lng</TableHead>
                  <TableHead>Radius (m)</TableHead>
                  <TableHead>Assets</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {sites.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell>{s.name}</TableCell>
                    <TableCell>{s.lat.toFixed(4)}</TableCell>
                    <TableCell>{s.lng.toFixed(4)}</TableCell>
                    <TableCell>{s.radius_m}</TableCell>
                    <TableCell>{s.asset_count}</TableCell>
                    <TableCell className="text-right">
                      <Link href={`/sites/${s.id}/compare`} className="text-sm text-primary hover:underline">
                        Compare
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Reports</CardTitle>
          <NewReportDialog projectId={id} comparisons={comparisons} />
        </CardHeader>
        <CardContent>
          {reports && reports.length === 0 ? (
            <p className="text-sm text-muted-foreground">No reports yet.</p>
          ) : null}
          {reports && reports.length > 0 ? (
            <ul className="divide-y">
              {reports.map((r) => (
                <li key={r.id} className="flex items-center justify-between py-2">
                  <Link href={`/reports/${r.id}`} className="text-sm hover:underline">
                    {r.date_from} → {r.date_to}
                  </Link>
                  <StatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
