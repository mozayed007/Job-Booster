"use client";

import { motion } from "framer-motion";
import { type LucideIcon, ArrowRight, Construction } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function PlaceholderPage({
  title,
  description,
  icon: Icon,
  endpoints,
  ctaHref,
  ctaLabel,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
  endpoints: string[];
  ctaHref?: string;
  ctaLabel?: string;
}) {
  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        description={description}
        icon={Icon}
        actions={<Badge variant="warning" className="gap-1"><Construction className="h-3 w-3" /> In Development</Badge>}
      />
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <Card className="overflow-hidden">
          <CardContent className="flex flex-col items-center py-20 text-center">
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20"
            >
              <Icon className="h-10 w-10 text-primary" />
            </motion.div>
            <h3 className="text-lg font-semibold">Backend ready · UI coming soon</h3>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              These endpoints are wired and tested. The polished interface for this feature ships in the next sprint.
            </p>

            <div className="mt-6 w-full max-w-md space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Backed by</p>
              {endpoints.map((e) => (
                <code
                  key={e}
                  className="block rounded-md bg-secondary/40 px-3 py-1.5 text-left font-mono text-xs text-muted-foreground"
                >
                  {e}
                </code>
              ))}
            </div>

            {ctaHref && ctaLabel && (
              <Button asChild variant="gradient" className="mt-8 gap-1.5">
                <a href={ctaHref}>{ctaLabel} <ArrowRight className="h-4 w-4" /></a>
              </Button>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
