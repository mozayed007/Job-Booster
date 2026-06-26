"use client";

import { Bot } from "lucide-react";
import { PlaceholderPage } from "@/components/placeholder-page";

export default function AgentsPage() {
  return (
    <PlaceholderPage
      title="Agent Experience"
      description="Explore the 9 config-driven AI agents and their MCP tools"
      icon={Bot}
      endpoints={[
        "GET /api/ax/tools",
        "GET /api/ax/tools/available",
        "GET /api/ax/agents",
      ]}
      ctaHref="/onboarding"
      ctaLabel="Try the Onboarding agent"
    />
  );
}
