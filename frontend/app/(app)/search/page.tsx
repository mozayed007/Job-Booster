"use client";

import { Search } from "lucide-react";
import { PlaceholderPage } from "@/components/placeholder-page";

export default function SearchPage() {
  return (
    <PlaceholderPage
      title="Semantic Search"
      description="Hybrid (keyword + vector) search across stored resumes and jobs"
      icon={Search}
      endpoints={[
        "POST /api/search/resumes",
        "POST /api/search/jobs",
        "POST /api/search/hybrid",
        "POST /api/search/index/resume/{id}",
        "POST /api/search/index/job/{id}",
        "GET  /api/search/stats",
      ]}
      ctaHref="/recommendations"
      ctaLabel="Try Recommendations"
    />
  );
}
