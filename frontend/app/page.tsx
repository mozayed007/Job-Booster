"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Zap, Clock, Layers, Boxes, GitBranch, ShieldCheck, FileText, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Reveal, Stagger, staggerItem } from "@/components/landing/reveal";
import { LandingNav } from "@/components/landing/nav";
import { HeroMock } from "@/components/landing/hero-mock";

const PIPELINE = [
  {
    step: "01",
    name: "Paste & Parse",
    desc: "Drop a resume + job description. CV Extractor maps your skills to the JD and flags missing metrics.",
    out: "Structured CV · relevance summary",
    icon: FileText,
  },
  {
    step: "02",
    name: "Review & Tailor",
    desc: "Every bullet gets a health score. Weak points are rewritten with the XYZ formula — no generic filler.",
    out: "Per-bullet reviews · 78/100 health",
    icon: GitBranch,
  },
  {
    step: "03",
    name: "Cover Letter",
    desc: "A grounded 4-paragraph letter built from your actual experience. Export to .docx in one click.",
    out: "Tailored letter · key-angle map",
    icon: Bot,
  },
  {
    step: "04",
    name: "Find & Track",
    desc: "Scored job listings across 6 criteria, then the whole package lands in your tracked applications.",
    out: "Scored jobs · tracked application",
    icon: Zap,
  },
];

const AGENTS = [
  { name: "CV Extractor", does: "Parses resume, maps skills to JD", gives: "Structured CV, missing metrics" },
  { name: "Resume Reviewer", does: "Diagnoses every bullet, scores health", gives: "Health score, rewrites" },
  { name: "Cover Letter", does: "Grounded 4-paragraph letter", gives: "Plain text + .docx" },
  { name: "Job Finder", does: "Generates queries, scores listings", gives: "Scored jobs w/ visa status" },
  { name: "Resume Tailor", does: "Graph-based restructuring for a role", gives: "Tailored content + notes" },
  { name: "Startup Scanner", does: "Scrapes career pages, ranks relevance", gives: "Extracted openings" },
  { name: "Outreach Agent", does: "Follow-ups, thank-yous, cold outreach", gives: "Ready-to-send emails" },
  { name: "Interview Coach", does: "Behavioral Qs, STAR stories", gives: "Full prep kit" },
  { name: "Discovery Sync", does: "Imports BigSet, syncs corpus", gives: "Ranked job corpus" },
];

const STACK = [
  "Pydantic AI",
  "LangChain",
  "LangGraph",
  "LiteLLM",
  "FastAPI",
  "Qdrant",
  "SQLAlchemy",
  "APScheduler",
  "Logfire",
  "Gradio",
];

const STATS = [
  { value: "9", label: "AI Agents", icon: Bot },
  { value: "≤60s", label: "Per Package", icon: Clock },
  { value: "100+", label: "LLM Models", icon: Layers },
  { value: "11", label: "API Routers", icon: Boxes },
];

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden">
      <LandingNav />

      {/* ── HERO ── */}
      <section className="relative noise">
        <div className="pointer-events-none absolute inset-0 bg-grid" />
        <div className="relative mx-auto grid max-w-6xl grid-cols-1 gap-16 px-6 pb-24 pt-36 lg:grid-cols-12 lg:gap-8 lg:pt-44">
          {/* Left: copy */}
          <div className="lg:col-span-6">
            <Reveal>
              <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/40 px-3 py-1 font-mono text-[11px] text-muted-foreground backdrop-blur-sm">
                <span className="h-1.5 w-1.5 animate-glow rounded-full bg-blue-400" />
                9 agents · typed pipeline · config-driven
              </span>
            </Reveal>

            <Reveal delay={0.05}>
              <h1 className="mt-6 font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl">
                Stop copy-pasting
                <br />
                <span className="text-muted-foreground">resumes.</span>
                <br />
                Run a pipeline.
              </h1>
            </Reveal>

            <Reveal delay={0.1}>
              <p className="mt-6 max-w-md text-lg leading-relaxed text-muted-foreground">
                Feed Job Booster a resume and a job description. Nine
                specialized agents parse, tailor, review, and track your whole
                application — in seconds, not hours.
              </p>
            </Reveal>

            <Reveal delay={0.15}>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Button asChild variant="gradient" size="lg">
                  <Link href="/register">
                    Start free <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg">
                  <Link href="#pipeline">See how it works</Link>
                </Button>
              </div>
            </Reveal>

            <Reveal delay={0.2}>
              <p className="mt-8 font-mono text-xs text-muted-foreground/70">
                No card. Bring one API key — OpenAI, Anthropic, or Gemini.
              </p>
            </Reveal>
          </div>

          {/* Right: product mock */}
          <div className="lg:col-span-6">
            <HeroMock />
          </div>
        </div>

        {/* trust marquee */}
        <div className="relative border-y border-border/50 bg-background/40 py-4">
          <div className="flex overflow-hidden">
            <div className="flex shrink-0 animate-marquee items-center gap-10 pr-10">
              {[...STACK, ...STACK].map((s, i) => (
                <span
                  key={i}
                  className="font-mono text-xs text-muted-foreground/60"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── PIPELINE ── */}
      <section id="pipeline" className="relative mx-auto max-w-6xl px-6 py-24">
        <Reveal>
          <div className="flex flex-col gap-4 border-l-2 border-blue-500/60 pl-5">
            <span className="font-mono text-xs uppercase tracking-widest text-blue-400">
              How it works
            </span>
            <h2 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
              From paste to tracked
              <br />
              application in 60 seconds.
            </h2>
            <p className="max-w-xl text-muted-foreground">
              Four typed steps. Each agent passes structured state to the next —
              artifacts collected, errors tracked, results persisted. No manual
              glue.
            </p>
          </div>
        </Reveal>

        <Stagger className="mt-14 grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
          {PIPELINE.map((p) => {
            const Icon = p.icon;
            return (
              <motion.div
                key={p.step}
                variants={staggerItem}
                className="group relative flex flex-col gap-3 bg-card p-6 transition-colors hover:bg-secondary/40"
              >
                <div className="flex items-center justify-between">
                  <Icon className="h-5 w-5 text-blue-400" />
                  <span className="font-mono text-xs text-muted-foreground/50">
                    {p.step}
                  </span>
                </div>
                <h3 className="font-display text-lg font-semibold tracking-tight">
                  {p.name}
                </h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {p.desc}
                </p>
                <div className="mt-auto pt-3">
                  <span className="font-mono text-[11px] text-cyan-400/80">
                    → {p.out}
                  </span>
                </div>
              </motion.div>
            );
          })}
        </Stagger>
      </section>

      {/* ── AGENTS ── */}
      <section id="agents" className="relative border-y border-border/50 bg-dots">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <div className="flex flex-col gap-4 border-l-2 border-cyan-500/60 pl-5">
              <span className="font-mono text-xs uppercase tracking-widest text-cyan-400">
                The roster
              </span>
              <h2 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
                Nine agents. One pipeline.
                <br />
                Each with a job.
              </h2>
              <p className="max-w-xl text-muted-foreground">
                Config-driven in <code className="font-mono text-xs text-foreground/80">agents.yaml</code> —
                prompts, skills, and output types per agent. Add or modify
                without touching application code.
              </p>
            </div>
          </Reveal>

          <Stagger className="mt-14 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {AGENTS.map((a, i) => (
              <motion.div
                key={a.name}
                variants={staggerItem}
                className="group relative overflow-hidden rounded-lg border border-border bg-card/60 p-5 transition-all hover:border-blue-500/40 hover:bg-card"
              >
                <span className="absolute right-4 top-4 font-mono text-[11px] text-muted-foreground/40 tabular-nums">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="font-display text-base font-semibold tracking-tight">
                  {a.name}
                </h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{a.does}</p>
                <div className="mt-4 flex items-center gap-2 border-t border-border/60 pt-3">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/60">
                    output
                  </span>
                  <span className="font-mono text-[11px] text-cyan-400/80">
                    {a.gives}
                  </span>
                </div>
              </motion.div>
            ))}
          </Stagger>
        </div>
      </section>

      {/* ── STATS ── */}
      <section id="stack" className="mx-auto max-w-6xl px-6 py-24">
        <div className="grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((s) => {
            const Icon = s.icon;
            return (
              <Reveal key={s.label} className="bg-card p-8">
                <Icon className="h-5 w-5 text-blue-400" />
                <div className="mt-4 font-display text-4xl font-bold tracking-tight tabular-nums">
                  {s.value}
                </div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {s.label}
                </div>
              </Reveal>
            );
          })}
        </div>

        {/* stack list */}
        <Reveal delay={0.1}>
          <div className="mt-12 flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/60">
              Built on
            </span>
            <div className="hairline mx-1 h-3 w-px" />
            {STACK.map((s) => (
              <span
                key={s}
                className="rounded-md border border-border/60 bg-card/40 px-2.5 py-1 font-mono text-[11px] text-muted-foreground"
              >
                {s}
              </span>
            ))}
          </div>
        </Reveal>
      </section>

      {/* ── CTA ── */}
      <section className="relative mx-auto max-w-6xl px-6 pb-24">
        <Reveal>
          <div className="noise relative overflow-hidden rounded-2xl border border-border bg-card/60 p-10 sm:p-16">
            <div className="conic-glow absolute -right-20 -top-20 h-64 w-64 blur-3xl" />
            <div className="relative grid gap-8 lg:grid-cols-2 lg:items-center">
              <div>
                <h2 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
                  Compress 30 minutes
                  <br />
                  into 30 seconds.
                </h2>
                <p className="mt-4 max-w-md text-muted-foreground">
                  Spin up an account, paste a resume, and watch nine agents run
                  a full application package. Bring your own API key.
                </p>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row lg:justify-end">
                <Button asChild variant="gradient" size="lg">
                  <Link href="/register">
                    Create account <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg">
                  <Link href="/login">I have an account</Link>
                </Button>
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-border/50">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-10 sm:flex-row">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-blue-500 to-cyan-500 text-white">
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </span>
            <span className="font-display text-sm font-semibold">Job Booster</span>
            <span className="font-mono text-[11px] text-muted-foreground/50">v1.0.0</span>
          </div>
          <div className="flex items-center gap-5 font-mono text-[11px] text-muted-foreground/60">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" /> MIT License
            </span>
            <Link href="/login" className="hover:text-foreground">Sign in</Link>
            <Link href="/register" className="hover:text-foreground">Get started</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
