import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { AssetStatus } from "@/lib/types";

const STYLE: Record<AssetStatus, string> = {
  pending: "bg-muted text-muted-foreground",
  processing: "bg-amber-100 text-amber-700",
  ready: "bg-emerald-100 text-emerald-700",
  failed: "bg-destructive/10 text-destructive",
};

export function StatusBadge({ status }: { status: AssetStatus }) {
  return (
    <Badge variant="secondary" className={cn("gap-1.5", STYLE[status])}>
      <span className="size-1.5 rounded-full bg-current" />
      {status}
    </Badge>
  );
}
