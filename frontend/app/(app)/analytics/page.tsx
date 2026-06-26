"use client";

import { BarChart3 } from "lucide-react";
import { PlaceholderPage } from "@/components/placeholder-page";

export default function AnalyticsPage() {
  return (
    <PlaceholderPage
      title="Analytics"
      description="Stats, trends, and skill market insights"
      icon={BarChart3}
      endpoints={[
        "GET /api/analytics/dashboard",
        "GET /api/analytics/resumes",
        "GET /api/analytics/jobs",
        "GET /api/analytics/skills",
        "GET /api/analytics/scanner",
      ]}
      ctaHref="/dashboard"
      ctaLabel="Back to dashboard"
    />
  );
}
