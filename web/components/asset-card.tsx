import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import { TagChips } from "@/components/tag-chips";
import type { AssetCard as AssetCardType } from "@/lib/types";

export function AssetCard({ asset, scoreBadge }: { asset: AssetCardType; scoreBadge?: string }) {
  return (
    <Link
      href={`/assets/${asset.id}`}
      className="block rounded-lg border overflow-hidden transition-colors hover:border-primary/50"
    >
      <div className="relative aspect-4/3 bg-muted">
        <img
          src={asset.thumb_url}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover"
        />
        {scoreBadge ? (
          <span className="absolute top-1.5 right-1.5 rounded bg-background/90 px-1.5 py-0.5 text-xs font-medium">
            {scoreBadge}
          </span>
        ) : null}
      </div>
      <div className="space-y-1.5 p-2">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-xs text-muted-foreground">{asset.site_name ?? "No site"}</span>
          <StatusBadge status={asset.status} />
        </div>
        <TagChips tags={asset.tags.slice(0, 3)} />
      </div>
    </Link>
  );
}
