"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
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
    <div className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground">
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

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const active = pathname === href || (href !== "/" && pathname.startsWith(href));
  return (
    <Link
      href={href}
      className={cn(
        "block rounded-md px-3 py-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
        active ? "bg-accent text-accent-foreground font-medium" : "text-muted-foreground",
      )}
    >
      {children}
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const projectMatch = pathname.match(/^\/projects\/([^/]+)/);
  const projectId = projectMatch?.[1];

  return (
    <div className="flex min-h-screen">
      <aside className="no-print w-56 shrink-0 border-r bg-muted/30 flex flex-col">
        <div className="px-3 py-4">
          <Link href="/" className="text-lg font-semibold px-3">
            FieldProof
          </Link>
        </div>
        <nav className="flex-1 space-y-1 px-2">
          <NavLink href="/">Dashboard</NavLink>
          <NavLink href="/search">Search</NavLink>
          <NavLink href="/credits">Credits</NavLink>
          {projectId ? (
            <div className="mt-4 space-y-1">
              <div className="px-3 pb-1 text-xs font-medium uppercase text-muted-foreground">
                Project
              </div>
              <NavLink href={`/projects/${projectId}`}>Overview</NavLink>
              <NavLink href={`/projects/${projectId}/upload`}>Upload</NavLink>
              <NavLink href={`/projects/${projectId}/library`}>Library</NavLink>
            </div>
          ) : null}
        </nav>
        <HealthDot />
      </aside>
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}
