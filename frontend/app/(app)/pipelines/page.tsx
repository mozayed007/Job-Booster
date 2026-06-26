"use client";

import { GitBranch } from "lucide-react";
import { PlaceholderPage } from "@/components/placeholder-page";

export default function PipelinesPage() {
  return (
    <PlaceholderPage
      title="Pipelines"
      description="Run discovery sync, daily scanner, full application, onboarding, and gap-recommendation pipelines"
      icon={GitBranch}
      endpoints={[
        "GET  /api/pipeline/list",
        "POST /api/pipeline/run",
        "GET  /api/pipeline/run/{job_id}",
        "POST /api/pipeline/apply",
        "POST /api/pipeline/apply/file",
      ]}
      ctaHref="/apply"
      ctaLabel="Run Apply Pipeline"
    />
  );
}
