"use client";

import { useEffect, useRef, useState } from "react";
import type { ApiErrorEnvelope } from "@/lib/types";

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

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...TUNNEL_HEADERS,
      ...init?.headers,
    },
  });

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
