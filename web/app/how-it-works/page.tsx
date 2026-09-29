import Link from "next/link";
import {
  ArrowLeftRight,
  CalendarClock,
  Check,
  CloudUpload,
  Crop,
  EyeOff,
  LayoutGrid,
  ScanSearch,
  BrainCircuit,
  FileText,
  GitBranch,
  Lock,
  Scale,
  Search,
  Upload,
  type LucideIcon,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const STEPS: { icon: LucideIcon; gradient: string; title: string; text: string; href: string; cta: string }[] = [
  {
    icon: Upload,
    gradient: "bg-grad-sunset",
    title: "Upload",
    text: "Field teams upload photos from phone or laptop straight to Cloudinary. Files never pass through our server.",
    href: "/upload",
    cta: "Upload photos",
  },
  {
    icon: BrainCircuit,
    gradient: "bg-grad-ocean",
    title: "Analyse",
    text: "A background worker reads the EXIF date and GPS, embeds the image with CLIP, tags activities, adds Cloudinary object detection and places it on the nearest site.",
    href: "/library",
    cta: "Browse the library",
  },
  {
    icon: Search,
    gradient: "bg-grad-lilac",
    title: "Search",
    text: "Describe what you need in plain English. The query is embedded with CLIP and matched against every photo with pgvector.",
    href: "/search",
    cta: "Try a search",
  },
  {
    icon: ArrowLeftRight,
    gradient: "bg-grad-mint",
    title: "Compare",
    text: "FieldProof suggests before/after pairs from the same site, at least 7 days apart, and estimates the change in green cover.",
    href: "/comparisons",
    cta: "See comparisons",
  },
  {
    icon: FileText,
    gradient: "bg-grad-sunset",
    title: "Report",
    text: "One click builds a report with metrics, a summary, before/after evidence, a print/PDF view and a social-media campaign kit.",
    href: "/reports",
    cta: "Open reports",
  },
  {
    icon: GitBranch,
    gradient: "bg-grad-ocean",
    title: "Trace",
    text: "Every derived image records its source photo, version, transformation and model. Open Lineage on any asset, comparison or kit item.",
    href: "/comparisons",
    cta: "Open a lineage",
  },
];

const CLOUDINARY: { icon: LucideIcon; name: string; what: string }[] = [
  { icon: CloudUpload, name: "Upload Widget", what: "Direct uploads from phone or laptop" },
  { icon: ScanSearch, name: "AI Content Analysis", what: "Object detection tags (coco_v2)" },
  { icon: Crop, name: "g_auto crops", what: "Subject-aware social squares and stories" },
  { icon: EyeOff, name: "e_blur_faces", what: "Faces blurred on every shared image" },
  { icon: LayoutGrid, name: "Collage", what: "Before/after collage for campaigns" },
  { icon: CalendarClock, name: "Image metadata", what: "EXIF capture date and GPS" },
];

const PRINCIPLES: { icon: LucideIcon; title: string; points: string[] }[] = [
  {
    icon: Scale,
    title: "Honest numbers",
    points: [
      "Every number comes from the database, never from the AI",
      "AI text that invents a number is rejected",
      "Green cover is labelled an estimate, with the mask viewable",
    ],
  },
  {
    icon: Lock,
    title: "Privacy",
    points: [
      "Faces blurred on everything made for sharing",
      "Consent required before any upload",
      "Device location used only when the uploader opts in",
    ],
  },
];

export default function HowItWorksPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-8 p-8">
      <PageHeader
        title="How it works"
        subtitle="From a phone photo in the field to a traceable impact report, in six steps."
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {STEPS.map(({ icon: Icon, gradient, title, text, href, cta }, i) => (
          <div key={title} className={`${gradient} flex flex-col justify-between gap-6 rounded-3xl p-6`}>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="grid size-11 place-items-center rounded-xl bg-white/50 backdrop-blur-sm">
                  <Icon className="size-5" />
                </span>
                <span className="text-4xl font-light text-foreground/40">{String(i + 1).padStart(2, "0")}</span>
              </div>
              <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
              <p className="text-sm leading-relaxed text-foreground/80">{text}</p>
            </div>
            <Button variant="dark" size="sm" className="w-fit" nativeButton={false} render={<Link href={href}>{cta}</Link>} />
          </div>
        ))}
      </div>

      <section className="space-y-4">
        <div>
          <p className="type-eyebrow text-primary">Powered by</p>
          <h2 className="type-title mt-1">Built on Cloudinary</h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {CLOUDINARY.map(({ icon: Icon, name, what }) => (
            <div key={name} className="flex items-center gap-4 rounded-2xl bg-card p-4 ring-1 ring-foreground/[0.05]">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-secondary text-secondary-foreground">
                <Icon className="size-5" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-bold">{name}</p>
                <p className="text-[13px] text-muted-foreground">{what}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        {PRINCIPLES.map(({ icon: Icon, title, points }) => (
          <Card key={title}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2.5">
                <span className="grid size-8 place-items-center rounded-lg bg-secondary text-secondary-foreground">
                  <Icon className="size-4" />
                </span>
                {title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2.5">
                {points.map((point) => (
                  <li key={point} className="flex items-start gap-2.5 text-sm">
                    <Check className="mt-0.5 size-4 shrink-0 text-emerald-600" />
                    {point}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}
