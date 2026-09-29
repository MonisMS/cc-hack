"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { CREDITS } from "@/lib/credits";
import { cn } from "@/lib/utils";

// "File:Mangrove plantation.jpg" -> "Mangrove plantation"
function title(file: string) {
  return file.replace(/^File:/, "").replace(/\.[a-z0-9]+$/i, "").replace(/_/g, " ");
}

function initials(author: string) {
  const words = author.replace(/^User:/, "").split(/\s+/).filter(Boolean);
  return (words[0]?.[0] ?? "?") + (words[1]?.[0] ?? "");
}

const LICENSE_DOT: Record<string, string> = {
  CC0: "bg-emerald-500",
  "Public domain": "bg-emerald-500",
  "CC BY 2.0": "bg-sky-500",
  "CC BY 4.0": "bg-sky-500",
};

// Stable pastel per author, so the initials circles vary but don't flicker between renders.
const AVATAR = ["bg-violet-100 text-violet-700", "bg-teal-100 text-teal-700", "bg-amber-100 text-amber-700", "bg-rose-100 text-rose-700", "bg-sky-100 text-sky-700"];
function avatarClass(author: string) {
  let h = 0;
  for (const ch of author) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return AVATAR[h % AVATAR.length];
}

const LICENSES = Object.entries(
  CREDITS.reduce<Record<string, number>>((acc, c) => {
    acc[c.license] = (acc[c.license] ?? 0) + 1;
    return acc;
  }, {}),
).sort((a, b) => b[1] - a[1]);

export default function CreditsPage() {
  const [license, setLicense] = useState<string | null>(null);
  const rows = license ? CREDITS.filter((c) => c.license === license) : CREDITS;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-8">
      <PageHeader
        title="Credits"
        subtitle={`The demo project uses ${CREDITS.length} openly licensed photos from Wikimedia Commons. Thank you to every photographer.`}
      />

      <div className="flex flex-wrap gap-2">
        {[["All licenses", CREDITS.length] as const, ...LICENSES].map(([name, n]) => {
          const value = name === "All licenses" ? null : name;
          const active = license === value;
          return (
            <button
              key={name}
              type="button"
              onClick={() => setLicense(value)}
              className={cn(
                "inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-[13px] font-medium ring-1 transition-colors",
                active
                  ? "bg-foreground text-background ring-foreground"
                  : "bg-card text-foreground ring-foreground/10 hover:ring-foreground/25",
              )}
            >
              {value ? <span className={cn("size-2 rounded-full", LICENSE_DOT[value] ?? "bg-violet-500")} /> : null}
              {name}
              <span className={active ? "text-background/60" : "text-muted-foreground"}>{n}</span>
            </button>
          );
        })}
      </div>

      <Card className="gap-0 py-0">
        <div className="hidden grid-cols-[1fr_14rem_9rem_6rem] gap-4 border-b px-5 py-3 md:grid">
          <span className="type-eyebrow text-muted-foreground">Photo</span>
          <span className="type-eyebrow text-muted-foreground">Author</span>
          <span className="type-eyebrow text-muted-foreground">License</span>
          <span className="type-eyebrow text-right text-muted-foreground">Source</span>
        </div>
        <ul className="divide-y">
          {rows.map((c) => (
            <li
              key={c.file}
              className="grid grid-cols-1 gap-2 px-5 py-3.5 transition-colors hover:bg-muted/50 md:grid-cols-[1fr_14rem_9rem_6rem] md:items-center md:gap-4"
            >
              <p className="truncate text-sm font-semibold" title={title(c.file)}>
                {title(c.file)}
              </p>
              <div className="flex min-w-0 items-center gap-2.5">
                <span
                  className={cn(
                    "grid size-7 shrink-0 place-items-center rounded-full text-[11px] font-bold uppercase",
                    avatarClass(c.author),
                  )}
                >
                  {initials(c.author)}
                </span>
                <span className="truncate text-sm text-muted-foreground" title={c.author}>
                  {c.author.replace(/^User:/, "")}
                </span>
              </div>
              <span className="flex items-center gap-2 text-[13px]">
                <span className={cn("size-2 rounded-full", LICENSE_DOT[c.license] ?? "bg-violet-500")} />
                {c.license}
              </span>
              <a
                href={c.source}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-[13px] font-medium text-primary hover:underline md:justify-self-end"
              >
                Wikimedia <ExternalLink className="size-3" />
              </a>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
