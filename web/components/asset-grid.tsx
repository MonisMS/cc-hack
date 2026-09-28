import { AssetCard } from "@/components/asset-card";
import type { AssetCard as AssetCardType } from "@/lib/types";

export function AssetGrid({ assets }: { assets: AssetCardType[] }) {
  if (assets.length === 0) {
    return <p className="text-sm text-muted-foreground py-8 text-center">No assets yet — upload some.</p>;
  }
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {assets.map((a) => (
        <AssetCard key={a.id} asset={a} />
      ))}
    </div>
  );
}
