import { ExternalLink, ImageIcon, Scale, User } from "lucide-react";
import { Card } from "@/components/ui/card";
import { CREDITS } from "@/lib/credits";

// "File:Mangrove plantation.jpg" -> "Mangrove plantation"
function title(file: string) {
  return file.replace(/^File:/, "").replace(/\.[a-z0-9]+$/i, "").replace(/_/g, " ");
}

function isOpen(license: string) {
  return license === "CC0" || license === "Public domain";
}

const LICENSE_COUNTS = Object.entries(
  CREDITS.reduce<Record<string, number>>((acc, c) => {
    acc[c.license] = (acc[c.license] ?? 0) + 1;
    return acc;
  }, {}),
).sort((a, b) => b[1] - a[1]);

export default function CreditsPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6 p-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Credits</h1>
        <p className="text-sm text-muted-foreground">
          The demo project uses openly licensed photos from Wikimedia Commons. Thank you to every photographer below.
        </p>
      </div>

      <div className="bg-grad-lilac flex flex-wrap items-center gap-x-6 gap-y-3 rounded-3xl p-5">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-white/45 backdrop-blur-sm">
            <ImageIcon className="size-[18px]" />
          </span>
          <div>
            <p className="text-3xl font-light tracking-tight">{CREDITS.length}</p>
            <p className="text-xs text-foreground/70">photos credited</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {LICENSE_COUNTS.map(([license, n]) => (
            <span key={license} className="rounded-full bg-white/60 px-3 py-1 text-xs font-medium backdrop-blur-sm">
              {license} · {n}
            </span>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CREDITS.map((c) => (
          <Card key={c.file} className="gap-3 px-5">
            <p className="line-clamp-2 min-h-10 font-medium leading-snug" title={title(c.file)}>
              {title(c.file)}
            </p>
            <div className="space-y-1.5 text-xs text-muted-foreground">
              <p className="flex items-center gap-2">
                <User className="size-3.5 shrink-0" />
                <span className="truncate" title={c.author}>{c.author}</span>
              </p>
              <p className="flex items-center gap-2">
                <Scale className="size-3.5 shrink-0" />
                <span
                  className={
                    isOpen(c.license)
                      ? "rounded-full bg-emerald-100 px-2 py-0.5 font-medium text-emerald-700"
                      : "rounded-full bg-secondary px-2 py-0.5 font-medium text-secondary-foreground"
                  }
                >
                  {c.license}
                </span>
              </p>
            </div>
            <a
              href={c.source}
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-fit items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              View on Wikimedia <ExternalLink className="size-3" />
            </a>
          </Card>
        ))}
      </div>
    </div>
  );
}
