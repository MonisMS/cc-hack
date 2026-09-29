import type { LucideIcon } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type StatGradient = "sunset" | "ocean" | "mint" | "lilac";

const GRADIENT: Record<StatGradient, string> = {
  sunset: "bg-grad-sunset",
  ocean: "bg-grad-ocean",
  mint: "bg-grad-mint",
  lilac: "bg-grad-lilac",
};

export function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  gradient,
  className,
}: {
  label: string;
  value: string | number | null;
  sub?: string;
  icon: LucideIcon;
  gradient: StatGradient;
  className?: string;
}) {
  return (
    <div
      className={cn(
        GRADIENT[gradient],
        "relative flex h-44 flex-col justify-between overflow-hidden rounded-3xl p-5 text-foreground print:h-auto print:gap-4",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="max-w-[10rem] text-[15px] leading-snug font-medium">{label}</p>
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/45 backdrop-blur-sm">
          <Icon className="size-[18px]" />
        </span>
      </div>
      <div>
        {value === null ? (
          <Skeleton className="h-11 w-16 bg-white/50" />
        ) : (
          <p className="text-5xl font-light tracking-tight">{value}</p>
        )}
        {sub ? <p className="mt-1 text-xs text-foreground/70">{sub}</p> : null}
      </div>
    </div>
  );
}
