import Link from "next/link";
import { MapPin, Play } from "lucide-react";
import { StatusBadge } from "@/components/status-badge";
import type { AssetCard as AssetCardType } from "@/lib/types";

export function AssetCard({ asset, scoreBadge }: { asset: AssetCardType; scoreBadge?: string }) {
  const tags = asset.tags.slice(0, 2);
  return (
    <Link
      href={`/assets/${asset.id}`}
      className="group relative block aspect-4/5 overflow-hidden rounded-2xl bg-muted shadow-[0_1px_2px_rgb(30_20_80/0.06)] transition-all hover:-translate-y-0.5 hover:shadow-[0_18px_36px_-18px_rgb(60_45_160/0.35)]"
    >
      <img
        src={asset.thumb_url}
        alt=""
        loading="lazy"
        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
      />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-2/3 bg-gradient-to-t from-black/75 via-black/30 to-transparent" />

      {scoreBadge ? (
        <span className="absolute right-2.5 top-2.5 rounded-full bg-white/90 px-2 py-0.5 text-[11px] font-semibold text-foreground backdrop-blur-sm">
          {scoreBadge} match
        </span>
      ) : null}
      {asset.resource_type === "video" ? (
        <span className="absolute left-1/2 top-[40%] grid size-11 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-black/45 text-white backdrop-blur-sm transition-transform group-hover:scale-110">
          <Play className="ml-0.5 size-5 fill-current" />
        </span>
      ) : null}
      {asset.status !== "ready" ? (
        <span className="absolute left-2.5 top-2.5">
          <StatusBadge status={asset.status} />
        </span>
      ) : null}

      <div className="absolute inset-x-0 bottom-0 space-y-2 p-3 text-white">
        <p className="flex items-center gap-1 truncate text-[13px] font-semibold">
          <MapPin className="size-3.5 shrink-0 opacity-80" />
          {asset.site_name ?? "Unassigned"}
        </p>
        {tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {tags.map((t) => (
              <span
                key={`${t.source}-${t.tag}`}
                className="rounded-full bg-white/20 px-2 py-0.5 text-[11px] font-medium backdrop-blur-md"
              >
                {t.tag.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </Link>
  );
}
