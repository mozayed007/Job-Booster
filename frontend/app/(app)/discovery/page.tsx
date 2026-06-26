"use client";

import { Compass } from "lucide-react";
import { PlaceholderPage } from "@/components/placeholder-page";

export default function DiscoveryPage() {
  return (
    <PlaceholderPage
      title="Discovery"
      description="BigSet imports, job board search, and ranked jobs"
      icon={Compass}
      endpoints={[
        "POST /api/discovery/search",
        "POST /api/discovery/index",
        "POST /api/discovery/bigset/sync",
        "POST /api/discovery/bigset/preview",
        "POST /api/discovery/bigset/import",
        "POST /api/discovery/bigset/remote/trigger",
        "GET  /api/discovery/sources",
        "GET  /api/discovery/jobs/ranked",
        "GET  /api/discovery/bigset/mappings",
        "GET  /api/discovery/bigset/remote/status",
      ]}
      ctaHref="/apply"
      ctaLabel="Run Apply instead"
    />
  );
}
