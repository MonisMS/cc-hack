import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import { TagChips } from "@/components/tag-chips";
import type { AssetCard as AssetCardType } from "@/lib/types";

export function AssetCard({ asset }: { asset: AssetCardType }) {
  return (
    <Link
      href={`/assets/${asset.id}`}
      className="block rounded-lg border overflow-hidden hover:border-primary transition-colors"
    >
      <div className="aspect-square bg-muted">
        <img src={asset.thumb_url} alt="" className="w-full h-full object-cover" loading="lazy" />
      </div>
      <div className="p-2 space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-muted-foreground truncate">{asset.site_name ?? "No site"}</span>
          <StatusBadge status={asset.status} />
        </div>
        {asset.captured_at ? (
          <p className="text-xs text-muted-foreground">{new Date(asset.captured_at).toLocaleDateString()}</p>
        ) : null}
        <TagChips tags={asset.tags.slice(0, 3)} />
      </div>
    </Link>
  );
}
