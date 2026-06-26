"use client";

import { Briefcase } from "lucide-react";
import { PlaceholderPage } from "@/components/placeholder-page";

export default function ApplicationsPage() {
  return (
    <PlaceholderPage
      title="Applications"
      description="Track and manage job applications with status updates"
      icon={Briefcase}
      endpoints={[
        "GET    /api/applications",
        "POST   /api/applications",
        "PUT    /api/applications/{app_id}",
        "DELETE /api/applications/{app_id}",
        "GET    /api/applications/stats",
      ]}
      ctaHref="/apply"
      ctaLabel="Start a new application"
    />
  );
}
