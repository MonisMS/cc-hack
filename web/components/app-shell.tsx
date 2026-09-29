"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import {
  ArrowLeftRight,
  Award,
  CloudOff,
  FileText,
  FolderKanban,
  Images,
  LayoutDashboard,
  Leaf,
  MapPin,
  Route,
  Search,
  Upload,
  type LucideIcon,
} from "lucide-react";
import { enterSnapshotMode, isSnapshotMode, onSnapshotMode, TUNNEL_HEADERS } from "@/lib/api";
import { cn } from "@/lib/utils";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function useSnapshotMode() {
  return useSyncExternalStore(onSnapshotMode, isSnapshotMode, () => false);
}

function HealthDot() {
  const [ok, setOk] = useState<boolean | null>(null);
  const snapshot = useSnapshotMode();

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/health`, { headers: TUNNEL_HEADERS, signal: AbortSignal.timeout(10000) })
      .then((res) => {
        if (cancelled) return;
        setOk(res.ok);
        if (!res.ok) enterSnapshotMode();
      })
      .catch((err) => {
        if (cancelled) return;
        // A slow reply isn't an outage; only a failed connection switches to the snapshot.
        if (err instanceof DOMException && err.name === "TimeoutError") return setOk(true);
        setOk(false);
        enterSnapshotMode();
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const state = snapshot ? "snapshot" : ok === null ? "checking" : ok ? "online" : "snapshot";
  return (
    <div className="flex items-center gap-2 rounded-xl bg-muted px-3 py-2.5 text-xs text-muted-foreground">
      <span
        className={cn(
          "size-2 rounded-full",
          state === "checking" && "bg-muted-foreground/40",
          state === "online" && "bg-green-500",
          state === "snapshot" && "bg-amber-500",
        )}
      />
      {state === "checking" ? "Checking live API..." : state === "online" ? "Live API online" : "Saved snapshot mode"}
    </div>
  );
}

function SnapshotBanner() {
  const snapshot = useSnapshotMode();
  if (!snapshot) return null;
  return (
    <div className="no-print flex items-center justify-center gap-2 bg-amber-100 px-4 py-2 text-center text-[13px] font-medium text-amber-900">
      <CloudOff className="size-4 shrink-0" />
      The live backend is offline right now, so you&apos;re viewing a saved snapshot of the real data. Browsing works;
      uploads and new reports need the live backend.
    </div>
  );
}

function NavLink({ href, icon: Icon, children }: { href: string; icon: LucideIcon; children: React.ReactNode }) {
  const pathname = usePathname();
  // Dashboard matches exactly; other links also match their sub-pages.
  const exact = href === "/";
  const active = exact ? pathname === href : pathname.startsWith(href);
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
        active ? "bg-accent text-accent-foreground font-medium" : "text-foreground/70",
      )}
    >
      <Icon className="size-[18px]" strokeWidth={active ? 2.2 : 1.8} />
      {children}
    </Link>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="px-3 pb-1.5 pt-5 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">{children}</div>;
}

export function AppShell({ children }: { children: React.ReactNode }) {

  return (
    <div className="flex min-h-screen">
      <aside className="no-print sticky top-0 h-screen w-60 shrink-0 border-r border-sidebar-border bg-sidebar flex flex-col">
        <div className="px-5 pt-6 pb-2">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-full bg-primary text-primary-foreground shadow-[0_6px_16px_-6px_var(--primary)]">
              <Leaf className="size-[18px]" />
            </span>
            <span className="type-title">FieldProof</span>
          </Link>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
          <SectionLabel>Overview</SectionLabel>
          <NavLink href="/" icon={LayoutDashboard}>Dashboard</NavLink>
          <NavLink href="/search" icon={Search}>Search</NavLink>
          <SectionLabel>Workspace</SectionLabel>
          <NavLink href="/projects" icon={FolderKanban}>Projects</NavLink>
          <NavLink href="/library" icon={Images}>Library</NavLink>
          <NavLink href="/sites" icon={MapPin}>Sites</NavLink>
          <NavLink href="/comparisons" icon={ArrowLeftRight}>Comparisons</NavLink>
          <NavLink href="/reports" icon={FileText}>Reports</NavLink>
          <NavLink href="/upload" icon={Upload}>Upload</NavLink>
          <SectionLabel>About</SectionLabel>
          <NavLink href="/how-it-works" icon={Route}>How it works</NavLink>
          <NavLink href="/credits" icon={Award}>Credits</NavLink>
        </nav>
        <div className="px-3 pb-4">
          <HealthDot />
        </div>
      </aside>
      <main className="flex-1 min-w-0">
        <SnapshotBanner />
        {children}
      </main>
    </div>
  );
}
