"use client";

import * as React from "react";
import { SegmentedProgress } from "@/components/segmented-progress";
import { useSession } from "@/components/session-provider";
import { Button } from "@/components/ui/button";
import { Sparkles, X } from "lucide-react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

export function OnboardingBanner() {
  const { user, loading } = useSession();
  const [dismissed, setDismissed] = React.useState(false);
  const show = !loading && user && !user.hasPersonalContext && !dismissed;

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          className="relative m-4 overflow-hidden rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-cyan-500/10 px-4 py-3"
        >
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-500/20">
              <Sparkles className="h-4 w-4 text-amber-400" />
            </span>
            <div className="flex-1">
              <p className="text-sm font-medium">
                Boost your recommendations with a 90-second chat
              </p>
              <p className="text-xs text-muted-foreground">
                Tell us your hobbies & interests. Used ONLY for enjoyable skill-gap recs — never your resume.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button asChild size="sm" variant="gradient">
                <Link href="/onboarding">Start chat</Link>
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8"
                onClick={() => setDismissed(true)}
                aria-label="Dismiss"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
          <div className="mt-2">
            <SegmentedProgress value={0} max={5} />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
