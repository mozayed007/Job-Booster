"use client";

import * as React from "react";
import { SessionProvider } from "@/components/session-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { CommandPalette } from "@/components/layout/command-palette";
import { OnboardingBanner } from "@/components/layout/onboarding-banner";
import { GradientBlobs } from "@/components/gradient-blobs";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <div className="relative min-h-screen">
        <GradientBlobs />
        <Sidebar />
        <div className="lg:pl-64">
          <Topbar />
          <OnboardingBanner />
          <main className="relative z-10 px-4 py-6 lg:px-8">{children}</main>
        </div>
        <CommandPalette />
      </div>
    </SessionProvider>
  );
}
