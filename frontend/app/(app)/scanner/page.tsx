"use client";

import { Radar } from "lucide-react";
import { PlaceholderPage } from "@/components/placeholder-page";

export default function ScannerPage() {
  return (
    <PlaceholderPage
      title="Startup Scanner"
      description="Batch-scan AI/ML startup career pages and rank openings by relevance"
      icon={Radar}
      endpoints={[
        "GET  /api/scanner/startups",
        "GET  /api/scanner/progress",
        "POST /api/scanner/scan/batch",
        "POST /api/scanner/scan/background",
        "GET  /api/scanner/jobs/top",
        "POST /api/scanner/reset",
        "GET  /api/scanner/cities",
      ]}
      ctaHref="/dashboard"
      ctaLabel="Back to dashboard"
    />
  );
}
