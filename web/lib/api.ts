"use client";

import { useEffect, useRef, useState } from "react";
import type { ApiErrorEnvelope, AssetCard as AssetCardType } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// The backend may sit behind a free ngrok tunnel, which serves a warning page instead of
// the API unless this header is present. Harmless everywhere else.
export const TUNNEL_HEADERS = { "ngrok-skip-browser-warning": "1" };

export class ApiErr extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

// ---------------------------------------------------------------------------------------------
// Snapshot fallback. If the live backend can't be reached (laptop off, tunnel down), reads are
// served from /snapshot.json: real API responses recorded by web/scripts/capture_snapshot.py.
// Photos still load because they come straight from Cloudinary. Writes are refused honestly.
// ---------------------------------------------------------------------------------------------
type SnapshotData = Record<string, unknown>;

const SNAPSHOT_URL = "/snapshot.json";
let snapshotData: Promise<SnapshotData> | null = null;
let snapshotMode = false;
const snapshotListeners = new Set<(on: boolean) => void>();

export function isSnapshotMode() {
  return snapshotMode;
}

export function onSnapshotMode(listener: (on: boolean) => void): () => void {
  snapshotListeners.add(listener);
  return () => snapshotListeners.delete(listener);
}

/** Switch every later request to the saved snapshot (also used by the sidebar health check). */
export function enterSnapshotMode() {
  if (snapshotMode) return;
  snapshotMode = true;
  snapshotListeners.forEach((l) => l(true));
}

function loadSnapshot(): Promise<SnapshotData> {
  snapshotData ??= fetch(SNAPSHOT_URL)
    .then((r) => (r.ok ? (r.json() as Promise<SnapshotData>) : {}))
    .catch(() => ({}));
  return snapshotData;
}

/** Same key format the capture script writes: "GET /path?query" or "POST /path <json body>". */
export function snapshotKey(path: string, init?: RequestInit): string {
  const method = (init?.method ?? "GET").toUpperCase();
  return method === "GET" ? `GET ${path}` : `${method} ${path} ${typeof init?.body === "string" ? init.body : ""}`;
}

type SearchBody = { query?: string; project_id?: string | null; site_id?: string | null; tag?: string | null };

/** Offline search for queries that weren't recorded: word match over the recorded photos' tags and sites. */
function searchSnapshot(data: SnapshotData, init?: RequestInit) {
  let body: SearchBody = {};
  try {
    body = JSON.parse(String(init?.body ?? "{}")) as SearchBody;
  } catch {
    // keep defaults
  }
  const assets = new Map<string, AssetCardType>();
  for (const [key, value] of Object.entries(data)) {
    if (!key.startsWith("GET /api/assets?")) continue;
    for (const a of (value as { items?: AssetCardType[] }).items ?? []) assets.set(a.id, a);
  }
  const words = (body.query ?? "").toLowerCase().split(/[^a-z]+/).filter((w) => w.length > 2);
  const items = [...assets.values()]
    .filter((a) => (!body.project_id || a.project_id === body.project_id) && (!body.site_id || a.site_id === body.site_id))
    .filter((a) => !body.tag || a.tags.some((t) => t.tag === body.tag))
    .map((a) => {
      const text = [...a.tags.map((t) => t.tag.replace(/_/g, " ")), a.site_name ?? ""].join(" ").toLowerCase();
      const hits = words.filter((w) => text.includes(w.replace(/s$/, ""))).length;
      return { asset: a, score: words.length ? hits / words.length / 2 : 0 };
    })
    .filter((h) => h.score > 0 || words.length === 0)
    .sort((x, y) => y.score - x.score)
    .slice(0, 20);
  return { items };
}

async function fromSnapshot<T>(path: string, init?: RequestInit): Promise<T> {
  const data = await loadSnapshot();
  const key = snapshotKey(path, init);
  if (key in data) return data[key] as T;
  if (path === "/api/search") return searchSnapshot(data, init) as T;
  const method = (init?.method ?? "GET").toUpperCase();
  throw new ApiErr(
    "OFFLINE",
    method === "GET"
      ? "This isn't in the saved snapshot while the live backend is offline."
      : "The live backend is offline, so changes are disabled in this saved snapshot.",
    0,
  );
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  if (snapshotMode) return fromSnapshot<T>(path, init);

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      // Fail over quickly instead of leaving a judge staring at spinners.
      signal: init?.signal ?? AbortSignal.timeout(path === "/api/search" ? 20000 : 10000),
      headers: {
        "Content-Type": "application/json",
        ...TUNNEL_HEADERS,
        ...init?.headers,
      },
    });
  } catch {
    // Network error, CORS-less tunnel error page, or timeout: the backend is unreachable.
    enterSnapshotMode();
    return fromSnapshot<T>(path, init);
  }

  // Anything that isn't JSON came from a proxy or tunnel error page, not from our API.
  const isJson = (res.headers.get("content-type") ?? "").includes("application/json");
  if (!isJson && res.status !== 204) {
    enterSnapshotMode();
    return fromSnapshot<T>(path, init);
  }

  if (!res.ok) {
    let envelope: ApiErrorEnvelope | null = null;
    try {
      envelope = (await res.json()) as ApiErrorEnvelope;
    } catch {
      // body wasn't JSON; fall through to a generic error below
    }
    if (envelope?.error) {
      throw new ApiErr(envelope.error.code, envelope.error.message, res.status, envelope.error.details);
    }
    throw new ApiErr("UNKNOWN", res.statusText || "request failed", res.status);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export function usePoll<T>(
  path: string | null,
  isDone: (data: T) => boolean,
  intervalMs = 2000,
): { data: T | null; error: ApiErr | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiErr | null>(null);
  const isDoneRef = useRef(isDone);
  useEffect(() => {
    isDoneRef.current = isDone;
  }, [isDone]);

  useEffect(() => {
    if (!path) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const tick = async () => {
      try {
        const result = await api<T>(path);
        if (cancelled) return;
        setData(result);
        setError(null);
        if (!isDoneRef.current(result)) {
          timer = setTimeout(tick, intervalMs);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof ApiErr ? err : new ApiErr("UNKNOWN", String(err), 0));
      }
    };

    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [path, intervalMs]);

  return { data, error };
}
