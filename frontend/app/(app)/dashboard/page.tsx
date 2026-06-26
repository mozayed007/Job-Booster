"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  FileText,
  Briefcase,
  Radar,
  Target,
  Sparkles,
  ArrowRight,
  Bot,
} from "lucide-react";
import Link from "next/link";
import { StatCard } from "@/components/stat-card";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useSession } from "@/components/session-provider";

const AGENTS = [
  { name: "CV Extractor", role: "Parses resume, maps skills to JD" },
  { name: "Resume Reviewer", role: "Per-bullet health scoring" },
  { name: "Cover Letter", role: "Grounded 4-paragraph letter" },
  { name: "Job Finder", role: "Scored listings across 6 criteria" },
  { name: "Resume Tailor", role: "Graph-based restructuring" },
  { name: "Startup Scanner", role: "Career page scraping + ranking" },
  { name: "Outreach Agent", role: "Follow-ups & cold outreach" },
  { name: "Interview Coach", role: "STAR stories from your resume" },
  { name: "Onboarding", role: "Personal context interview" },
];

export default function DashboardPage() {
  const { user } = useSession();
  const firstName = user?.name?.split(" ")[0] ?? "there";

  return (
    <div className="space-y-8">
      <PageHeader
        title={`Welcome back, ${firstName}`}
        description="Your AI job-application pipeline at a glance"
        icon={Sparkles}
        actions={
          <Button asChild variant="gradient">
            <Link href="/apply">
              Run Apply Pipeline <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Resumes" value="—" icon={FileText} delay={0.05} hint="Connect backend" accent="blue" />
        <StatCard label="Applications" value="—" icon={Briefcase} delay={0.1} accent="cyan" />
        <StatCard label="Scanned Startups" value="—" icon={Radar} delay={0.15} accent="sky" />
        <StatCard label="Skill Gaps" value="—" icon={Target} delay={0.2} accent="amber" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-primary" />
                Your Agent Roster
              </CardTitle>
              <Badge>9 agents</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {AGENTS.map((agent, i) => (
                <motion.div
                  key={agent.name}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 + i * 0.04 }}
                  className="flex items-center gap-3 rounded-lg border border-border bg-secondary/20 p-3 transition-colors hover:border-primary/40"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-br from-blue-500/30 to-cyan-500/30 text-xs font-bold text-primary">
                    {agent.name[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium">{agent.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{agent.role}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {[
              { label: "Tailor a resume", href: "/apply", icon: Sparkles, accent: "text-blue-400" },
              { label: "Chat onboarding", href: "/onboarding", icon: Bot, accent: "text-cyan-400" },
              { label: "Find skill gaps", href: "/recommendations", icon: Target, accent: "text-amber-400" },
              { label: "Scan startups", href: "/scanner", icon: Radar, accent: "text-sky-400" },
            ].map((a) => {
              const Icon = a.icon;
              return (
                <Link
                  key={a.href}
                  href={a.href}
                  className="flex items-center gap-3 rounded-lg border border-border bg-secondary/20 p-3 transition-all hover:border-primary/40 hover:bg-secondary/40"
                >
                  <Icon className={`h-4 w-4 ${a.accent}`} />
                  <span className="flex-1 text-sm font-medium">{a.label}</span>
                  <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                </Link>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
