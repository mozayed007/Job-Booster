"use client";

import { motion } from "framer-motion";
import { type LucideIcon, TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  icon: Icon,
  hint,
  trend,
  accent = "blue",
  delay = 0,
}: {
  label: string;
  value: string | number;
  icon: LucideIcon;
  hint?: string;
  trend?: { value: string; positive: boolean };
  accent?: "blue" | "cyan" | "sky" | "emerald" | "amber";
  delay?: number;
}) {
  const accents: Record<string, string> = {
    blue: "from-blue-500/20 to-blue-500/0 text-blue-400",
    cyan: "from-cyan-500/20 to-cyan-500/0 text-cyan-400",
    sky: "from-sky-500/20 to-sky-500/0 text-sky-400",
    emerald: "from-emerald-500/20 to-emerald-500/0 text-emerald-400",
    amber: "from-amber-500/20 to-amber-500/0 text-amber-400",
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
    >
      <Card className="relative overflow-hidden p-5">
        <div
          className={cn(
            "absolute right-0 top-0 h-24 w-24 rounded-full bg-gradient-to-br blur-2xl",
            accents[accent]
          )}
        />
        <div className="relative flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {label}
            </p>
            <p className="text-3xl font-bold tracking-tight">{value}</p>
            {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
          </div>
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br",
              accents[accent]
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        </div>
        {trend && (
          <div className="relative mt-3 flex items-center gap-1 text-xs">
            <TrendingUp
              className={cn(
                "h-3 w-3",
                trend.positive ? "text-emerald-400" : "text-destructive rotate-180"
              )}
            />
            <span className={trend.positive ? "text-emerald-400" : "text-destructive"}>
              {trend.value}
            </span>
          </div>
        )}
      </Card>
    </motion.div>
  );
}
