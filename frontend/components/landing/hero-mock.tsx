"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

type Stage = {
  id: string;
  name: string;
  fn: string;
  dur: string;
  out: string;
};

const STAGES: Stage[] = [
  {
    id: "cv",
    name: "CV Extractor",
    fn: "cv_extractor",
    dur: "2.1s",
    out: "resume.json · 14 bullets · 32 skills mapped",
  },
  {
    id: "review",
    name: "Resume Reviewer",
    fn: "resume_reviewer",
    dur: "4.4s",
    out: "health 78/100 · 6 weak bullets flagged",
  },
  {
    id: "cover",
    name: "Cover Letter",
    fn: "cover_letter",
    dur: "1.2s",
    out: "4-paragraph letter · grounded in your metrics",
  },
  {
    id: "jobs",
    name: "Job Finder",
    fn: "job_finder",
    dur: "—",
    out: "queued · 6 scoring criteria",
  },
];

function StatusIcon({ state }: { state: "done" | "active" | "queued" }) {
  if (state === "done")
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-400">
        <Check className="h-3 w-3" strokeWidth={3} />
      </span>
    );
  if (state === "active")
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-500/15 text-blue-400">
        <Loader2 className="h-3 w-3 animate-spin" />
      </span>
    );
  return (
    <span className="flex h-5 w-5 items-center justify-center rounded-full text-muted-foreground/50">
      <Circle className="h-2.5 w-2.5 fill-current" />
    </span>
  );
}

export function HeroMock() {
  const [active, setActive] = React.useState(0);

  React.useEffect(() => {
    const t = setInterval(() => {
      setActive((a) => (a + 1) % (STAGES.length + 1));
    }, 1800);
    return () => clearInterval(t);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, rotateX: 6 }}
      animate={{ opacity: 1, y: 0, rotateX: 0 }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
      className="relative"
      style={{ perspective: 1200 }}
    >
      {/* glow */}
      <div className="conic-glow absolute -inset-6 -z-10 blur-2xl" />

      <div className="overflow-hidden rounded-xl border border-border bg-card/80 shadow-2xl backdrop-blur-xl">
        {/* window chrome */}
        <div className="flex items-center gap-2 border-b border-border/70 bg-background/60 px-4 py-3">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-500/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/70" />
          <span className="ml-3 font-mono text-[11px] text-muted-foreground">
            POST /api/pipeline/full-application
          </span>
          <span className="ml-auto rounded bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] text-emerald-400">
            200 · streaming
          </span>
        </div>

        {/* pipeline body */}
        <div className="space-y-1 p-4">
          <div className="mb-3 flex items-baseline justify-between">
            <span className="font-mono text-xs text-muted-foreground">
              Apply Pipeline · run #4821
            </span>
            <span className="font-mono text-[10px] text-muted-foreground/70">
              PipelineState
            </span>
          </div>

          {STAGES.map((s, i) => {
            const state =
              i < active ? "done" : i === active ? "active" : "queued";
            return (
              <motion.div
                key={s.id}
                animate={{
                  opacity: i > active ? 0.45 : 1,
                  backgroundColor:
                    i === active
                      ? "hsl(213 94% 62% / 0.06)"
                      : "hsl(0 0% 0% / 0)",
                }}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5",
                  i === active && "ring-1 ring-blue-500/20"
                )}
              >
                <StatusIcon state={state} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">
                      {s.name}
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground/70">
                      {s.fn}()
                    </span>
                  </div>
                  <AnimatePresence mode="wait">
                    {state !== "queued" && (
                      <motion.div
                        key={state}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="truncate font-mono text-[11px] text-muted-foreground"
                      >
                        {s.out}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
                <span className="font-mono text-[11px] text-muted-foreground/70 tabular-nums">
                  {i === active ? "··" : s.dur}
                </span>
              </motion.div>
            );
          })}

          {/* output artifact */}
          <div className="mt-3 rounded-lg border border-border/70 bg-background/50 p-3">
            <div className="mb-1.5 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
              <span className="font-mono text-[11px] text-muted-foreground">
                artifacts[&quot;cover_letter&quot;]
              </span>
            </div>
            <p className="font-mono text-[11px] leading-relaxed text-muted-foreground/80">
              <span className="text-blue-400">&quot;</span>My 3 years at Stripe
              scaling payouts 4× directly maps to your cross-border volume
              goals<span className="text-blue-400">&quot;</span> — grounded in
              your resume, no fabrication.
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
