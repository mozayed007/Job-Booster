"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  LayoutDashboard,
  Sparkles,
  Compass,
  Radar,
  Search,
  Target,
  Briefcase,
  BarChart3,
  GitBranch,
  Bot,
  User,
  MessageSquareHeart,
} from "lucide-react";

const PAGES: { label: string; href: string; icon: typeof LayoutDashboard; group: string }[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, group: "Overview" },
  { label: "Onboarding Chat", href: "/onboarding", icon: MessageSquareHeart, group: "Overview" },
  { label: "Apply", href: "/apply", icon: Sparkles, group: "Career" },
  { label: "Discovery", href: "/discovery", icon: Compass, group: "Career" },
  { label: "Scanner", href: "/scanner", icon: Radar, group: "Career" },
  { label: "Search", href: "/search", icon: Search, group: "Career" },
  { label: "Recommendations", href: "/recommendations", icon: Target, group: "Career" },
  { label: "Applications", href: "/applications", icon: Briefcase, group: "Track" },
  { label: "Analytics", href: "/analytics", icon: BarChart3, group: "Track" },
  { label: "Pipelines", href: "/pipelines", icon: GitBranch, group: "Track" },
  { label: "Agents", href: "/agents", icon: Bot, group: "Track" },
  { label: "Account", href: "/account", icon: User, group: "You" },
];

export function CommandPalette() {
  const [open, setOpen] = React.useState(false);
  const router = useRouter();

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const groups = PAGES.reduce<Record<string, typeof PAGES>>((acc, p) => {
    (acc[p.group] = acc[p.group] || []).push(p);
    return acc;
  }, {});

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search pages… (⌘K)" />
      <CommandList>
        <CommandEmpty>No page found.</CommandEmpty>
        {Object.entries(groups).map(([group, items]) => (
          <CommandGroup key={group} heading={group}>
            {items.map((p) => {
              const Icon = p.icon;
              return (
                <CommandItem
                  key={p.href}
                  onSelect={() => {
                    router.push(p.href);
                    setOpen(false);
                  }}
                >
                  <Icon />
                  <span>{p.label}</span>
                </CommandItem>
              );
            })}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  );
}
