"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiErr } from "@/lib/api";
import type { Comparison } from "@/lib/types";

export function NewReportDialog({
  projectId,
  comparisons,
}: {
  projectId: string;
  comparisons: Comparison[];
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!dateFrom || !dateTo) return;
    setSubmitting(true);
    try {
      const res = await api<{ report_id: string }>("/api/reports", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          date_from: dateFrom,
          date_to: dateTo,
          comparison_ids: Array.from(selected),
        }),
      });
      toast.success("Report generating...");
      setOpen(false);
      router.push(`/reports/${res.report_id}`);
    } catch (err) {
      toast.error(err instanceof ApiErr ? err.message : "Could not create report");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button>New report</Button>} />
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>New report</DialogTitle>
            <DialogDescription>
              Summarizes field evidence in a date range, plus any before/after comparisons you pick.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="report-date-from">From</Label>
                <Input
                  id="report-date-from"
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="report-date-to">To</Label>
                <Input
                  id="report-date-to"
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label>Before/after comparisons</Label>
              {comparisons.length === 0 ? (
                <p className="text-sm text-muted-foreground">None ready yet.</p>
              ) : (
                <div className="max-h-48 overflow-y-auto rounded-md border p-2 space-y-1">
                  {comparisons.map((c) => (
                    <label key={c.id} className="flex items-center gap-2 text-sm py-1">
                      <input
                        type="checkbox"
                        checked={selected.has(c.id)}
                        onChange={() => toggle(c.id)}
                        className="size-4"
                      />
                      {c.site_name} · {c.delta_green_pct_rounded != null ? `${c.delta_green_pct_rounded > 0 ? "+" : ""}${c.delta_green_pct_rounded} pts` : "—"}
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={submitting || !dateFrom || !dateTo}>
              {submitting ? "Creating..." : "Create report"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
