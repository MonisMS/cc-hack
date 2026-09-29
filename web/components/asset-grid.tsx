import { AssetCard } from "@/components/asset-card";
import type { AssetCard as AssetCardType } from "@/lib/types";

export function AssetGrid({
  assets,
  scores,
}: {
  assets: AssetCardType[];
  scores?: Record<string, number>;
}) {
  if (assets.length === 0) return null;
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {assets.map((a) => (
        <AssetCard
          key={a.id}
          asset={a}
          scoreBadge={scores?.[a.id] != null ? `${Math.round(scores[a.id] * 100)}%` : undefined}
        />
      ))}
    </div>
  );
}
