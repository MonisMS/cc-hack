import { TrendingDown, TrendingUp } from "lucide-react";

export function GreenDelta({ value }: { value: number | null }) {
  if (value == null) return <span className="text-xs text-muted-foreground">no estimate</span>;
  const up = value > 0;
  const flat = value === 0;
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <span
      className={
        flat
          ? "inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-semibold text-muted-foreground"
          : up
            ? "inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700"
            : "inline-flex items-center gap-1 rounded-full bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-700"
      }
    >
      {flat ? null : <Icon className="size-3.5" />}
      {up ? "+" : ""}
      {value} pts green
    </span>
  );
}
