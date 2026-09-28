"use client";

import { CldUploadWidget } from "next-cloudinary";
import type { CloudinaryUploadWidgetInfo, CloudinaryUploadWidgetResults } from "next-cloudinary";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiErr, usePoll } from "@/lib/api";
import type { AssetDetail } from "@/lib/types";

const UPLOAD_PRESET = process.env.NEXT_PUBLIC_CLOUDINARY_IMAGE_PRESET ?? "fp_image";

type TrackedUpload = { assetId: string; filename: string };

function UploadStatusRow({ assetId, filename }: { assetId: string; filename: string }) {
  const { data } = usePoll<AssetDetail>(
    `/api/assets/${assetId}`,
    (a) => a.status === "ready" || a.status === "failed",
  );
  const status = data?.status ?? "pending";
  return (
    <li className="flex items-center justify-between py-2 text-sm">
      <span className="truncate">{filename}</span>
      <div className="flex items-center gap-2">
        <Badge variant={status === "ready" ? "default" : status === "failed" ? "destructive" : "secondary"}>
          {status}
        </Badge>
        {status === "ready" ? (
          <Link href={`/assets/${assetId}`} className="text-primary hover:underline">
            View
          </Link>
        ) : null}
      </div>
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
      if (!asInfo.image_metadata) {
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
    <div className="p-8 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">Upload photos</h1>
        <p className="text-muted-foreground">
          Photos only. Videos are supported by the backend but not exposed here.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 pt-6">
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-0.5 size-4"
            />
            I have permission to use these photos.
          </label>

          <div className="flex items-center gap-3">
            <Button type="button" variant="outline" onClick={useMyLocation} disabled={locating}>
              {locating ? "Locating..." : "Use my location"}
            </Button>
            {deviceLat != null && deviceLng != null ? (
              <span className="text-xs text-muted-foreground">
                {deviceLat.toFixed(4)}, {deviceLng.toFixed(4)}
              </span>
            ) : (
              <span className="text-xs text-muted-foreground">optional</span>
            )}
          </div>

          <CldUploadWidget
            uploadPreset={UPLOAD_PRESET}
            onSuccess={handleUploadSuccess}
            options={{
              sources: ["local", "camera"],
              multiple: true,
              maxFiles: 20,
              clientAllowedFormats: ["jpg", "jpeg", "png", "webp", "heic"],
            }}
          >
            {({ open }) => (
              <Button type="button" disabled={!consent} onClick={() => open()}>
                Upload photos
              </Button>
            )}
          </CldUploadWidget>
        </CardContent>
      </Card>

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
