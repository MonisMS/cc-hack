"use client";

import { CldUploadWidget } from "next-cloudinary";
import type { CloudinaryUploadWidgetInfo, CloudinaryUploadWidgetResults } from "next-cloudinary";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Check, Film, ImageUp, LocateFixed, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiErr, usePoll } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { AssetDetail } from "@/lib/types";

const UPLOAD_PRESET = process.env.NEXT_PUBLIC_CLOUDINARY_IMAGE_PRESET ?? "fp_image";
const VIDEO_PRESET = process.env.NEXT_PUBLIC_CLOUDINARY_VIDEO_PRESET ?? "fp_video";

// Themes Cloudinary's upload popup to match the app (palette/fonts keys per the Upload Widget docs).
const WIDGET_STYLES = {
  palette: {
    window: "#FFFFFF",
    windowBorder: "#E4E2F0",
    tabIcon: "#6B5CE7",
    menuIcons: "#6E6A85",
    textDark: "#1E1B2E",
    textLight: "#FFFFFF",
    link: "#6B5CE7",
    action: "#6B5CE7",
    inactiveTabIcon: "#9E98BF",
    error: "#E5484D",
    inProgress: "#6B5CE7",
    complete: "#1FA971",
    sourceBg: "#F7F6FC",
  },
  fonts: {
    "'Plus Jakarta Sans', sans-serif": "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap",
  },
};

type TrackedUpload = { assetId: string; filename: string };

function UploadStatusRow({ assetId, filename }: { assetId: string; filename: string }) {
  const { data } = usePoll<AssetDetail>(
    `/api/assets/${assetId}`,
    (a) => a.status === "ready" || a.status === "failed",
  );
  const status = data?.status ?? "pending";
  return (
    <li className="flex items-center gap-3 py-3">
      {data?.thumb_url ? (
        <img src={data.thumb_url} alt="" className="size-12 shrink-0 rounded-xl object-cover" />
      ) : (
        <div className="size-12 shrink-0 animate-pulse rounded-xl bg-muted" />
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{filename}</p>
        <p className="truncate text-xs text-muted-foreground">
          {status === "ready"
            ? `${data?.site_name ?? "No site"} · ${data?.tags.slice(0, 3).map((t) => t.tag.replace(/_/g, " ")).join(", ") || "no tags"}`
            : status === "failed"
              ? data?.error ?? "Analysis failed"
              : "Reading date and location, tagging with AI..."}
        </p>
      </div>
      <StatusBadge status={status} />
      {status === "ready" ? (
        <Button size="sm" variant="outline" nativeButton={false} render={<Link href={`/assets/${assetId}`}>View</Link>} />
      ) : null}
    </li>
  );
}

export default function UploadPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [consent, setConsent] = useState(false);
  const [deviceLat, setDeviceLat] = useState<number | null>(null);
  const [deviceLng, setDeviceLng] = useState<number | null>(null);
  const [locating, setLocating] = useState(false);
  const [uploads, setUploads] = useState<TrackedUpload[]>([]);
  const loggedFirstResult = useRef(false);

  function useMyLocation() {
    if (!navigator.geolocation) {
      toast.error("Geolocation isn't available in this browser");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setDeviceLat(pos.coords.latitude);
        setDeviceLng(pos.coords.longitude);
        setLocating(false);
        toast.success("Location captured");
      },
      () => {
        setLocating(false);
        toast.error("Could not get your location");
      },
    );
  }

  async function handleUploadSuccess(results: CloudinaryUploadWidgetResults) {
    const info = results?.info;
    if (!info || typeof info === "string") return;
    const asInfo = info as CloudinaryUploadWidgetInfo & { info?: { detection?: unknown } };

    if (!loggedFirstResult.current) {
      loggedFirstResult.current = true;
      console.log("Cloudinary upload result.info:", asInfo);
      if (asInfo.resource_type === "image" && !asInfo.image_metadata) {
        toast.warning(
          "This upload has no EXIF image_metadata — the worker will fall back to one Admin API call for it.",
        );
      }
    }

    try {
      const res = await api<{ asset_id: string; status: string; job_id: number | null }>(
        "/api/assets/register",
        {
          method: "POST",
          body: JSON.stringify({
            project_id: projectId,
            cld_public_id: asInfo.public_id,
            cld_asset_id: asInfo.asset_id,
            cld_version: asInfo.version,
            resource_type: asInfo.resource_type,
            format: asInfo.format,
            width: asInfo.width,
            height: asInfo.height,
            bytes: asInfo.bytes,
            duration_s: (asInfo as { duration?: number }).duration ?? null,
            secure_url: asInfo.secure_url,
            device_lat: deviceLat,
            device_lng: deviceLng,
            consent_confirmed: consent,
            image_metadata: asInfo.image_metadata ?? null,
            detection: asInfo.info?.detection ?? null,
          }),
        },
      );
      setUploads((prev) => [{ assetId: res.asset_id, filename: asInfo.original_filename }, ...prev]);
    } catch (err) {
      toast.error(err instanceof ApiErr ? err.message : "Could not register upload");
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-8">
      <PageHeader title="Upload photos" subtitle="Add field photos to this project. Each one is analysed automatically within seconds." />

      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-4">
          <button
            type="button"
            onClick={() => setConsent((c) => !c)}
            className={cn(
              "flex w-full items-center gap-4 rounded-2xl bg-card p-4 text-left ring-1 transition-colors",
              consent ? "ring-primary/60" : "ring-foreground/[0.06] hover:ring-primary/30",
            )}
          >
            <span
              className={cn(
                "grid size-10 shrink-0 place-items-center rounded-xl transition-colors",
                consent ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground",
              )}
            >
              {consent ? <Check className="size-5" /> : <ShieldCheck className="size-5" />}
            </span>
            <span>
              <span className="block text-sm font-semibold">I have permission to use these photos</span>
              <span className="block text-xs text-muted-foreground">Required. People in the photos agreed to be photographed.</span>
            </span>
          </button>

          <div className="flex items-center gap-4 rounded-2xl bg-card p-4 ring-1 ring-foreground/[0.06]">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-secondary text-secondary-foreground">
              <LocateFixed className="size-5" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">Location</p>
              <p className="text-xs text-muted-foreground">
                {deviceLat != null && deviceLng != null
                  ? `Using ${deviceLat.toFixed(4)}, ${deviceLng.toFixed(4)} for photos without GPS`
                  : "Optional. Used only for photos that don't carry their own GPS."}
              </p>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={useMyLocation} disabled={locating}>
              {locating ? "Locating..." : deviceLat != null ? "Update" : "Use my location"}
            </Button>
          </div>

          <div
            className={cn(
              "flex flex-col items-center gap-3 rounded-3xl border-2 border-dashed border-primary/30 bg-gradient-to-br from-violet-50 via-white to-teal-50 px-6 py-12 text-center",
              !consent && "opacity-60",
            )}
          >
            <span className="grid size-14 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-[0_10px_24px_-10px_var(--primary)]">
              <ImageUp className="size-6" />
            </span>
            <span className="type-title">{consent ? "Add field photos or videos" : "Confirm permission to start"}</span>
            <span className="text-sm text-muted-foreground">
              Photos: JPG, PNG, WEBP or HEIC, up to 20 at a time · Videos: MP4 or MOV, up to 100 MB · camera works on phones
            </span>
            <div className="mt-2 flex flex-wrap justify-center gap-2">
              <CldUploadWidget
                uploadPreset={UPLOAD_PRESET}
                onSuccess={handleUploadSuccess}
                options={{
                  sources: ["local", "camera"],
                  multiple: true,
                  maxFiles: 20,
                  clientAllowedFormats: ["jpg", "jpeg", "png", "webp", "heic"],
                  styles: WIDGET_STYLES,
                }}
              >
                {({ open }) => (
                  <Button type="button" size="lg" disabled={!consent} onClick={() => open()}>
                    <ImageUp /> Upload photos
                  </Button>
                )}
              </CldUploadWidget>
              <CldUploadWidget
                uploadPreset={VIDEO_PRESET}
                onSuccess={handleUploadSuccess}
                options={{
                  sources: ["local", "camera"],
                  resourceType: "video",
                  multiple: false,
                  maxFileSize: 100_000_000,
                  clientAllowedFormats: ["mp4", "mov"],
                  styles: WIDGET_STYLES,
                }}
              >
                {({ open }) => (
                  <Button type="button" size="lg" variant="outline" disabled={!consent} onClick={() => open()}>
                    <Film /> Upload a video
                  </Button>
                )}
              </CldUploadWidget>
            </div>
          </div>
        </div>

        <Card className="h-fit">
          <CardHeader>
            <CardTitle>What happens next</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-3">
              {[
                "Uploads go straight to Cloudinary",
                "Videos: three keyframes are analysed",
                "Date and GPS are read from the photo",
                "It's placed on the nearest site",
                "CLIP and object detection tag it",
                "It becomes searchable in plain English",
              ].map((step, i) => (
                <li key={step} className="flex items-center gap-3 text-sm">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-secondary text-xs font-bold text-secondary-foreground">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>

      {uploads.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>This session&apos;s uploads</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y">
              {uploads.map((u) => (
                <UploadStatusRow key={u.assetId} assetId={u.assetId} filename={u.filename} />
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
