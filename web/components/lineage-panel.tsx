"use client";

import { useEffect, useState } from "react";
import { CopyIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiErr } from "@/lib/api";
import type { LineageRecord } from "@/lib/types";

function isImageUrl(url: string) {
  return /\.(jpe?g|png|webp|gif)(\?|$)/i.test(url) || url.includes("res.cloudinary.com");
}

function LineageEntry({ record }: { record: LineageRecord }) {
  return (
    <div className="rounded-lg border p-3 space-y-2 text-sm">
      <div>
        <div className="text-xs font-medium text-muted-foreground">Source</div>
        <div className="font-mono text-xs break-all">
          {record.source_public_ids.length > 0
            ? record.source_public_ids
                .map((id, i) => `${id}${record.source_versions[i] ? `@v${record.source_versions[i]}` : ""}`)
                .join(", ")
            : "—"}
        </div>
      </div>

      {record.transformation ? (
        <div>
          <div className="text-xs font-medium text-muted-foreground">Transformation</div>
          <div className="flex items-center gap-2">
            <code className="text-xs break-all flex-1">{record.transformation}</code>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={() => navigator.clipboard.writeText(record.transformation ?? "")}
            >
              <CopyIcon />
              <span className="sr-only">Copy</span>
            </Button>
          </div>
        </div>
      ) : null}

      <div>
        <div className="text-xs font-medium text-muted-foreground">Output ({record.output_kind})</div>
        {record.output_ref ? (
          isImageUrl(record.output_ref) ? (
            <a href={record.output_ref} target="_blank" rel="noreferrer">
              <img src={record.output_ref} alt="" className="mt-1 max-h-32 rounded border object-cover" />
            </a>
          ) : (
            <a href={record.output_ref} target="_blank" rel="noreferrer" className="text-xs text-primary break-all hover:underline">
              {record.output_ref}
            </a>
          )
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </div>

      <div className="text-xs text-muted-foreground pt-1 border-t">
        {[record.tool, record.model].filter(Boolean).join(" · ") || "—"}
        {" · "}
        {new Date(record.created_at).toLocaleString()}
      </div>
    </div>
  );
}

export function LineagePanel({
  entityType,
  entityId,
  trigger,
}: {
  entityType: LineageRecord["entity_type"];
  entityId: string;
  trigger?: React.ReactElement;
}) {
  const [open, setOpen] = useState(false);
  const [records, setRecords] = useState<LineageRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    async function load() {
      setRecords(null);
      setError(null);
      try {
        const res = await api<{ items: LineageRecord[] }>(
          `/api/lineage?entity_type=${entityType}&entity_id=${entityId}`,
        );
        if (!cancelled) setRecords(res.items);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiErr ? err.message : "Could not load lineage");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [open, entityType, entityId]);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger render={trigger ?? <Button variant="outline">Lineage</Button>} />
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Lineage</SheetTitle>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-3">
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {!error && !records ? (
            <>
              <Skeleton className="h-24" />
              <Skeleton className="h-24" />
            </>
          ) : null}
          {records && records.length === 0 ? (
            <p className="text-sm text-muted-foreground">No lineage records yet.</p>
          ) : null}
          {records?.map((r) => <LineageEntry key={r.id} record={r} />)}
        </div>
      </SheetContent>
    </Sheet>
  );
}
