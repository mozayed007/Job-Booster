"use client";

import { cn } from "@/lib/utils";

export function SegmentedProgress({
  value,
  max,
  className,
}: {
  value: number;
  max: number;
  className?: string;
}) {
  const segments = Array.from({ length: max });
  return (
    <div className={cn("flex gap-1", className)}>
      {segments.map((_, i) => (
        <div
          key={i}
          className={cn(
            "h-1 flex-1 rounded-full transition-colors",
            i < value ? "bg-emerald-500" : "bg-secondary"
          )}
        />
      ))}
    </div>
  );
}
