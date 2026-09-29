"use client";

import { CopyIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { api, ApiErr } from "@/lib/api";
import type { LineageRecord } from "@/lib/types";

function isImageUrl(url: string) {
  return /\.(jpe?g|png|webp|gif)(\?|$)/i.test(url) || url.includes("res.cloudinary.com");
}

function LineageRow({ record }: { record: LineageRecord }) {
  return (
    <div className="space-y-2 rounded-md border p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium">{record.output_kind}</span>
        <span className="text-xs text-muted-foreground">
          {new Date(record.created_at).toLocaleString()}
        </span>
      </div>

      {record.source_public_ids.length > 0 ? (
        <div className="text-xs text-muted-foreground">
          source: {record.source_public_ids.join(", ")}
          {record.source_versions.length > 0 ? ` (v${record.source_versions.join(", v")})` : ""}
        </div>
      ) : null}

      {record.transformation ? (
        <div className="flex items-center gap-2">
          <code className="flex-1 truncate rounded bg-muted px-2 py-1 text-xs">
            {record.transformation}
          </code>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7 shrink-0"
            onClick={() => {
              navigator.clipboard.writeText(record.transformation ?? "");
              toast.success("Copied");
            }}
          >
            <CopyIcon className="size-3.5" />
          </Button>
        </div>
      ) : null}

      {record.output_ref ? (
        isImageUrl(record.output_ref) ? (
          <a href={record.output_ref} target="_blank" rel="noreferrer">
            <img
              src={record.output_ref}
              alt=""
              className="max-h-32 rounded border object-contain"
            />
          </a>
        ) : (
          <a
            href={record.output_ref}
            target="_blank"
            rel="noreferrer"
            className="block truncate text-xs text-primary hover:underline"
          >
            {record.output_ref}
          </a>
        )
      ) : null}

      <div className="text-xs text-muted-foreground">
        {[record.tool, record.model].filter(Boolean).join(" · ") || "—"}
      </div>
    </div>
  );
}

// Keyed by entityId so each entity gets a fresh mount (and fresh null state)
// instead of needing to reset state imperatively inside an effect.
function LineageList({
  entityType,
  entityId,
}: {
  entityType: "asset" | "comparison" | "report" | "kit";
  entityId: string;
}) {
  const [records, setRecords] = useState<LineageRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<{ items: LineageRecord[] }>(
      `/api/lineage?entity_type=${entityType}&entity_id=${entityId}`,
    )
      .then((res) => setRecords(res.items))
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load lineage"));
  }, [entityType, entityId]);

  return (
    <div className="space-y-3 px-4 pb-4">
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {records === null && !error ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : null}
      {records && records.length === 0 ? (
        <p className="text-sm text-muted-foreground">No lineage recorded yet.</p>
      ) : null}
      {records?.map((r) => <LineageRow key={r.id} record={r} />)}
    </div>
  );
}

export function LineagePanel({
  entityType,
  entityId,
  trigger,
}: {
  entityType: "asset" | "comparison" | "report" | "kit";
  entityId: string;
  trigger?: React.ReactElement;
}) {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger render={trigger ?? <Button variant="outline">Lineage</Button>} />
      <SheetContent className="overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Lineage</SheetTitle>
          <SheetDescription>Where this came from and how it was made.</SheetDescription>
        </SheetHeader>
        {open ? <LineageList key={entityId} entityType={entityType} entityId={entityId} /> : null}
      </SheetContent>
    </Sheet>
  );
}
