"use client";

import { useEffect, useState } from "react";
import { api, ApiErr } from "@/lib/api";
import type { Project } from "@/lib/types";

export type WithProject<T> = T & { project: Project };

/**
 * Loads every project, then one per-project list endpoint for each of them, and returns
 * the merged items tagged with their project. Used by the workspace-wide pages
 * (Sites, Comparisons, Reports) since the API lists these per project.
 */
export function useAcrossProjects<T>(path: (projectId: string) => string) {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [items, setItems] = useState<WithProject<T>[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<{ items: Project[] }>("/api/projects")
      .then((res) => {
        setProjects(res.items);
        return Promise.all(
          res.items.map((p) =>
            api<{ items: T[] }>(path(p.id)).then((r) => r.items.map((item) => ({ ...item, project: p }))),
          ),
        );
      })
      .then((lists) => setItems(lists.flat()))
      .catch((err) => setError(err instanceof ApiErr ? err.message : "Could not load data"));
    // path is a pure URL builder; loading once on mount is intended.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { projects, items, error };
}

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
