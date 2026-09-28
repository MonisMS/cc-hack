import { Badge } from "@/components/ui/badge";

type Status = "pending" | "processing" | "ready" | "failed";

const VARIANT: Record<Status, "secondary" | "default" | "destructive"> = {
  pending: "secondary",
  processing: "secondary",
  ready: "default",
  failed: "destructive",
};

const LABEL: Record<Status, string> = {
  pending: "Pending",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: Status }) {
  return <Badge variant={VARIANT[status]}>{LABEL[status]}</Badge>;
}
