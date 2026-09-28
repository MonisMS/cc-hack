import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Tag } from "@/lib/types";

const VARIANT: Record<Tag["source"], "secondary" | "outline" | "default"> = {
  clip: "secondary",
  cld_detection: "outline",
  manual: "default",
};

export function TagChips({ tags, className }: { tags: Tag[]; className?: string }) {
  if (tags.length === 0) return null;
  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {tags.map((t, i) => (
        <Badge key={`${t.source}-${t.tag}-${i}`} variant={VARIANT[t.source]}>
          {t.tag}
        </Badge>
      ))}
    </div>
  );
}
