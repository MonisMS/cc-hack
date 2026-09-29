import { Badge } from "@/components/ui/badge";
import type { Tag } from "@/lib/types";

// clip = "suggested" (secondary), cld_detection = outline, manual = solid (default).
const VARIANT: Record<Tag["source"], "secondary" | "outline" | "default"> = {
  clip: "secondary",
  cld_detection: "outline",
  manual: "default",
};

export function TagChips({ tags }: { tags: Tag[] }) {
  if (tags.length === 0) {
    return <span className="text-xs text-muted-foreground">No tags yet</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {tags.map((t) => (
        <Badge key={`${t.source}-${t.tag}`} variant={VARIANT[t.source]} title={t.source}>
          {t.tag}
        </Badge>
      ))}
    </div>
  );
}
