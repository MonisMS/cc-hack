"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiErr } from "@/lib/api";
import type { Site } from "@/lib/types";

export function AddSiteDialog({ projectId, onCreated }: { projectId: string; onCreated: (site: Site) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [radiusM, setRadiusM] = useState("200");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const latNum = Number(lat);
    const lngNum = Number(lng);
    if (!name.trim() || Number.isNaN(latNum) || Number.isNaN(lngNum)) return;
    setSubmitting(true);
    try {
      const site = await api<Site>(`/api/projects/${projectId}/sites`, {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          lat: latNum,
          lng: lngNum,
          radius_m: Number(radiusM) || 200,
        }),
      });
      toast.success(`Site "${site.name}" added`);
      onCreated(site);
      setOpen(false);
      setName("");
      setLat("");
      setLng("");
      setRadiusM("200");
    } catch (err) {
      toast.error(err instanceof ApiErr ? err.message : "Could not add site");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline">Add site</Button>} />
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add site</DialogTitle>
            <DialogDescription>Coordinates place uploaded photos automatically.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="site-name">Name</Label>
              <Input id="site-name" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="site-lat">Latitude</Label>
                <Input
                  id="site-lat"
                  type="number"
                  step="any"
                  min={-90}
                  max={90}
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="site-lng">Longitude</Label>
                <Input
                  id="site-lng"
                  type="number"
                  step="any"
                  min={-180}
                  max={180}
                  value={lng}
                  onChange={(e) => setLng(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="site-radius">Radius (m)</Label>
              <Input
                id="site-radius"
                type="number"
                min={20}
                max={5000}
                value={radiusM}
                onChange={(e) => setRadiusM(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Adding..." : "Add site"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
