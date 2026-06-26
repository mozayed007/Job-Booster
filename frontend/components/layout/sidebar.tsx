"use client";

import * as React from "react";
import {
  LayoutDashboard,
  FileText,
  Sparkles,
  Radar,
  Search,
  Compass,
  Target,
  Briefcase,
  BarChart3,
  GitBranch,
  Bot,
  User,
  MessageSquareHeart,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
};

const SECTIONS: { heading: string; items: NavItem[] }[] = [
  {
    heading: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/onboarding", label: "Onboarding", icon: MessageSquareHeart, badge: "AI" },
    ],
  },
  {
    heading: "Career Engine",
    items: [
      { href: "/apply", label: "Apply", icon: Sparkles, badge: "Core" },
      { href: "/discovery", label: "Discovery", icon: Compass },
      { href: "/scanner", label: "Scanner", icon: Radar },
      { href: "/search", label: "Search", icon: Search },
      { href: "/recommendations", label: "Recommendations", icon: Target },
    ],
  },
  {
    heading: "Track & Learn",
    items: [
      { href: "/applications", label: "Applications", icon: Briefcase },
      { href: "/analytics", label: "Analytics", icon: BarChart3 },
      { href: "/pipelines", label: "Pipelines", icon: GitBranch },
      { href: "/agents", label: "Agents", icon: Bot },
    ],
  },
  {
    heading: "You",
    items: [{ href: "/account", label: "Account", icon: User }],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="fixed left-0 top-0 z-30 hidden h-screen w-64 flex-col border-r border-border bg-card/40 backdrop-blur-xl lg:flex">
      <div className="flex h-16 items-center gap-2 px-6">
        <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 glow-primary">
          <FileText className="h-5 w-5 text-white" />
        </div>
        <div className="flex flex-col leading-none">
          <span className="text-sm font-bold tracking-tight">Job Booster</span>
          <span className="text-[10px] text-muted-foreground">AI Application Engine</span>
        </div>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
        {SECTIONS.map((section) => (
          <div key={section.heading} className="space-y-1">
            <p className="px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
              {section.heading}
            </p>
            {section.items.map((item) => {
              const active =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all",
                    active
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="flex-1">{item.label}</span>
                  {item.badge && (
                    <span className="rounded-full bg-primary/15 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-primary">
                      {item.badge}
                    </span>
                  )}
                  {active && (
                    <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary" />
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="border-t border-border p-4">
        <div className="rounded-lg bg-gradient-to-br from-blue-500/10 to-cyan-500/10 p-3">
          <p className="text-xs font-medium text-foreground">9 AI Agents</p>
          <p className="text-[11px] text-muted-foreground">Working in your pipeline</p>
        </div>
      </div>
    </aside>
  );
}
