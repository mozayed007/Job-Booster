"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Sparkles,
  Upload,
  FileText,
  Briefcase,
  Loader2,
  CheckCircle2,
  ArrowRight,
  Download,
  Wand2,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const PIPELINE_STEPS = [
  { id: "cv_extractor", name: "CV Extractor", desc: "Parsing your resume…" },
  { id: "resume_reviewer", name: "Resume Reviewer", desc: "Scoring bullets…" },
  { id: "cover_letter_generator", name: "Cover Letter", desc: "Writing letter…" },
  { id: "job_finder", name: "Job Finder", desc: "Scoring listings…" },
];

export default function ApplyPage() {
  const [resumeText, setResumeText] = React.useState("");
  const [resumeFile, setResumeFile] = React.useState<File | null>(null);
  const [jobText, setJobText] = React.useState("");
  const [running, setRunning] = React.useState(false);
  const [stepIdx, setStepIdx] = React.useState(-1);
  const [result, setResult] = React.useState<null | {
    tailored_resume?: string;
    cover_letter?: string;
    analysis?: string;
  }>(null);

  const fileInput = React.useRef<HTMLInputElement>(null);

  async function runPipeline() {
    if (!resumeText && !resumeFile) {
      toast.error("Add a resume first");
      return;
    }
    if (!jobText.trim()) {
      toast.error("Paste a job description");
      return;
    }
    setRunning(true);
    setResult(null);
    setStepIdx(0);
    try {
      const fd = new FormData();
      if (resumeFile) fd.append("file", resumeFile);
      else fd.append("resumeText", resumeText);
      fd.append("jobText", jobText);
      // One call to the backend's unified apply pipeline: it parses, tailors,
      // writes the cover letter, runs analysis, and tracks the application.
      const r = await fetch("/api/apply/run", { method: "POST", body: fd });
      if (r.status === 401) {
        window.location.href = "/login";
        return;
      }
      const pd = (await r.json().catch(() => ({}))) as {
        detail?: string;
        data?: { tailored_content?: string; cover_letter?: string };
      };
      if (!r.ok) throw new Error(pd.detail ?? "Pipeline failed");
      setStepIdx(PIPELINE_STEPS.length);
      setResult({
        tailored_resume: pd.data?.tailored_content ?? "",
        cover_letter: pd.data?.cover_letter,
      });
      toast.success("Application package ready!");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Pipeline failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Apply Pipeline"
        description="Upload your resume + a job description. Get a tailored resume, cover letter, and analysis in seconds."
        icon={Sparkles}
        actions={
          <Button onClick={runPipeline} variant="gradient" disabled={running} className="gap-1.5">
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
            Run Pipeline
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Resume input */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4 text-primary" /> Your Resume
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div
              className={cn(
                "rounded-lg border-2 border-dashed border-border p-6 text-center transition-colors hover:border-primary/50",
                resumeFile && "border-primary/50 bg-primary/5"
              )}
              onClick={() => fileInput.current?.click()}
              role="button"
            >
              <input
                ref={fileInput}
                type="file"
                accept=".pdf,.docx,.txt,.tex"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) {
                    setResumeFile(f);
                    toast.success(`Loaded ${f.name}`);
                  }
                }}
              />
              {resumeFile ? (
                <div className="flex flex-col items-center gap-1">
                  <CheckCircle2 className="h-6 w-6 text-emerald-400" />
                  <p className="text-sm font-medium">{resumeFile.name}</p>
                  <p className="text-xs text-muted-foreground">{(resumeFile.size / 1024).toFixed(0)} KB</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-1 text-muted-foreground">
                  <Upload className="h-6 w-6" />
                  <p className="text-sm">Click to upload PDF, DOCX, TXT, or TEX</p>
                </div>
              )}
            </div>
            <textarea
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              placeholder="…or paste your resume text here"
              className="h-40 w-full rounded-md border border-input bg-background/40 p-3 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </CardContent>
        </Card>

        {/* Job input */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Briefcase className="h-4 w-4 text-primary" /> Job Description
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              value={jobText}
              onChange={(e) => setJobText(e.target.value)}
              placeholder="Paste the full job description here…"
              className="h-64"
            />
            <p className="mt-2 text-xs text-muted-foreground">
              {jobText.length} chars · parsed and scored by the Job Finder agent
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline progress */}
      <AnimatePresence>
        {running && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <Card>
              <CardContent className="py-6">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {PIPELINE_STEPS.map((step, i) => {
                    const status = i < stepIdx ? "done" : i === stepIdx ? "active" : "pending";
                    return (
                      <motion.div
                        key={step.id}
                        animate={status === "active" ? { scale: 1.02 } : { scale: 1 }}
                        className={cn(
                          "rounded-lg border p-4 transition-colors",
                          status === "done" && "border-emerald-500/40 bg-emerald-500/5",
                          status === "active" && "border-primary/50 bg-primary/5",
                          status === "pending" && "border-border opacity-50"
                        )}
                      >
                        <div className="flex items-center gap-2">
                          {status === "done" ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                          ) : status === "active" ? (
                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                          ) : (
                            <div className="h-4 w-4 rounded-full border-2 border-muted" />
                          )}
                          <span className="text-sm font-medium">{step.name}</span>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">{step.desc}</p>
                      </motion.div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Sparkles className="h-4 w-4 text-primary" /> Tailored Output
                </CardTitle>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" className="gap-1.5">
                    <Download className="h-3.5 w-3.5" /> Export DOCX
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <pre className="max-h-96 overflow-auto rounded-lg bg-secondary/40 p-4 text-xs leading-relaxed whitespace-pre-wrap">
                  {result.tailored_resume ?? "No tailored output produced. Check pipeline artifacts."}
                </pre>
              </CardContent>
            </Card>

            {result.cover_letter && (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <FileText className="h-4 w-4 text-primary" /> Cover Letter
                  </CardTitle>
                  <Badge variant="success">Grounded</Badge>
                </CardHeader>
                <CardContent>
                  <pre className="max-h-96 overflow-auto rounded-lg bg-secondary/40 p-4 text-xs leading-relaxed whitespace-pre-wrap">
                    {result.cover_letter}
                  </pre>
                </CardContent>
              </Card>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
