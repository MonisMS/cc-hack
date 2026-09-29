import { Badge } from "@/components/ui/badge";
import type { AssetStatus } from "@/lib/types";

const VARIANT: Record<AssetStatus, "secondary" | "default" | "destructive"> = {
  pending: "secondary",
  processing: "secondary",
  ready: "default",
  failed: "destructive",
};

export function StatusBadge({ status }: { status: AssetStatus }) {
  return <Badge variant={VARIANT[status]}>{status}</Badge>;
}
