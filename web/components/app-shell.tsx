"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Award, FolderKanban, Images, LayoutDashboard, Leaf, Search, Upload, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function HealthDot() {
  const [ok, setOk] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/health`)
      .then((res) => {
        if (!cancelled) setOk(res.ok);
      })
      .catch(() => {
        if (!cancelled) setOk(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex items-center gap-2 rounded-xl bg-muted px-3 py-2.5 text-xs text-muted-foreground">
      <span
        className={cn(
          "size-2 rounded-full",
          ok === null && "bg-muted-foreground/40",
          ok === true && "bg-green-500",
          ok === false && "bg-destructive",
        )}
      />
      {ok === null ? "checking API..." : ok ? "API online" : "API offline"}
    </div>
  );
}

function NavLink({ href, icon: Icon, children }: { href: string; icon: LucideIcon; children: React.ReactNode }) {
  const pathname = usePathname();
  // Dashboard and project overview match exactly; other links also match their sub-pages.
  const exact = href === "/" || /^\/projects\/[^/]+$/.test(href);
  const active = exact ? pathname === href : pathname.startsWith(href);
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
        active ? "bg-accent text-accent-foreground font-medium" : "text-foreground/70",
      )}
    >
      <Icon className="size-[18px]" strokeWidth={active ? 2.2 : 1.8} />
      {children}
    </Link>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="px-3 pb-2 pt-6 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">{children}</div>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const projectMatch = pathname.match(/^\/projects\/([^/]+)/);
  const projectId = projectMatch?.[1];

  return (
    <div className="flex min-h-screen">
      <aside className="no-print sticky top-0 h-screen w-60 shrink-0 border-r border-sidebar-border bg-sidebar flex flex-col">
        <div className="px-5 pt-6 pb-2">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-full bg-primary text-primary-foreground shadow-[0_6px_16px_-6px_var(--primary)]">
              <Leaf className="size-[18px]" />
            </span>
            <span className="text-lg font-semibold tracking-tight">FieldProof</span>
          </Link>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          <SectionLabel>Overview</SectionLabel>
          <NavLink href="/" icon={LayoutDashboard}>Dashboard</NavLink>
          <NavLink href="/search" icon={Search}>Search</NavLink>
          {projectId ? (
            <>
              <SectionLabel>Project</SectionLabel>
              <NavLink href={`/projects/${projectId}`} icon={FolderKanban}>Overview</NavLink>
              <NavLink href={`/projects/${projectId}/upload`} icon={Upload}>Upload</NavLink>
              <NavLink href={`/projects/${projectId}/library`} icon={Images}>Library</NavLink>
            </>
          ) : null}
          <SectionLabel>About</SectionLabel>
          <NavLink href="/credits" icon={Award}>Credits</NavLink>
        </nav>
        <div className="px-3 pb-4">
          <HealthDot />
        </div>
      </aside>
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}
