import { ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";

function Slot({ url, className }: { url?: string; className?: string }) {
  return url ? (
    <img src={url} alt="" loading="lazy" className={cn("h-full w-full object-cover", className)} />
  ) : (
    <div className={cn("grid h-full w-full place-items-center bg-muted text-muted-foreground/40", className)}>
      <ImageIcon className="size-5" />
    </div>
  );
}

/**
 * Edge-to-edge photo header for cards: one large photo plus up to two (layout="feature")
 * or an even strip of four (layout="strip"). Missing photos show a quiet placeholder.
 */
export function PhotoMosaic({
  urls,
  layout = "feature",
  className,
}: {
  urls: string[];
  layout?: "feature" | "strip" | "square";
  className?: string;
}) {
  if (layout === "strip") {
    return (
      <div className={cn("grid h-32 grid-cols-4 gap-0.5 overflow-hidden", className)}>
        {[0, 1, 2, 3].map((i) => (
          <Slot key={i} url={urls[i]} />
        ))}
      </div>
    );
  }
  if (layout === "square") {
    return (
      <div className={cn("grid grid-cols-2 grid-rows-2 gap-0.5 overflow-hidden", className)}>
        {[0, 1, 2, 3].map((i) => (
          <Slot key={i} url={urls[i]} />
        ))}
      </div>
    );
  }
  return (
    <div className={cn("grid h-44 grid-cols-3 grid-rows-2 gap-0.5 overflow-hidden", className)}>
      <Slot url={urls[0]} className="col-span-2 row-span-2" />
      <Slot url={urls[1]} />
      <Slot url={urls[2]} />
    </div>
  );
}

/** "4 sites · 69 photos · 2 reports" style metadata line. */
export function MetaLine({ items, className }: { items: (string | null | false | undefined)[]; className?: string }) {
  const shown = items.filter(Boolean) as string[];
  return (
    <p className={cn("flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-muted-foreground", className)}>
      {shown.map((item, i) => (
        <span key={item} className="flex items-center gap-2">
          {i > 0 ? <span className="size-1 rounded-full bg-muted-foreground/40" /> : null}
          {item}
        </span>
      ))}
    </p>
  );
}
