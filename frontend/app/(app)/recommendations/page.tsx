"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Target,
  Sparkles,
  Loader2,
  ArrowRight,
  BookOpen,
  Clock,
  Heart,
  Lightbulb,
  AlertCircle,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import type { EnjoyableRecsResponse, Recommendation } from "@/lib/types";
import { useSession } from "@/components/session-provider";
import Link from "next/link";

export default function RecommendationsPage() {
  const { user } = useSession();
  const [resumeId, setResumeId] = React.useState("");
  const [jobId, setJobId] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [data, setData] = React.useState<EnjoyableRecsResponse | null>(null);

  async function run() {
    const rid = Number(resumeId);
    const jid = Number(jobId);
    if (!rid || !jid) {
      toast.error("Enter both IDs");
      return;
    }
    setLoading(true);
    setData(null);
    try {
      const res = await fetch(`/api/proxy/recommendations/enjoyable/${rid}/${jid}?max_per_gap=3`);
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        const j = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(j.detail ?? "Failed");
      }
      const d = (await res.json()) as EnjoyableRecsResponse;
      setData(d);
      toast.success(`Generated ${d.recommendations.length} personalized recommendations`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  const recsByGap = React.useMemo(() => {
    if (!data) return new Map<string, Recommendation[]>();
    const m = new Map<string, Recommendation[]>();
    for (const r of data.recommendations) {
      const arr = m.get(r.target_gap) ?? [];
      arr.push(r);
      m.set(r.target_gap, arr);
    }
    return m;
  }, [data]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recommendations"
        description="Skill-gap analysis + enjoyable projects/courses that match your personal context"
        icon={Target}
      />

      {/* Onboarding CTA when no personal context */}
      {data && !data.has_personal_context && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-cyan-500/10 p-4"
        >
          <div className="flex flex-wrap items-center gap-3">
            <Heart className="h-5 w-5 text-amber-400" />
            <div className="flex-1">
              <p className="text-sm font-medium">Recs are generic right now</p>
              <p className="text-xs text-muted-foreground">
                Complete onboarding so the gap-recommendation agent can personalize by your hobbies & interests.
              </p>
            </div>
            <Button asChild size="sm" variant="gradient">
              <Link href="/onboarding">Personalize <ArrowRight className="h-3.5 w-3.5" /></Link>
            </Button>
          </div>
        </motion.div>
      )}

      <Card>
        <CardContent className="flex flex-wrap items-end gap-3 py-4">
          <div className="space-y-1.5">
            <Label htmlFor="rid" className="text-xs">Resume ID</Label>
            <Input id="rid" value={resumeId} onChange={(e) => setResumeId(e.target.value)} placeholder="1" className="w-32" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="jid" className="text-xs">Job ID</Label>
            <Input id="jid" value={jobId} onChange={(e) => setJobId(e.target.value)} placeholder="1" className="w-32" />
          </div>
          <Button onClick={run} variant="gradient" disabled={loading} className="gap-1.5">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Generate
          </Button>
          {!user?.hasPersonalContext && (
            <Badge variant="warning" className="ml-auto">No personal context</Badge>
          )}
        </CardContent>
      </Card>

      <Tabs defaultValue="enjoyable">
        <TabsList>
          <TabsTrigger value="enjoyable" className="gap-1.5">
            <Heart className="h-3.5 w-3.5" /> Enjoyable Recs
          </TabsTrigger>
          <TabsTrigger value="gaps" className="gap-1.5">
            <AlertCircle className="h-3.5 w-3.5" /> Skill Gaps
          </TabsTrigger>
        </TabsList>

        <TabsContent value="enjoyable">
          {loading && <RecSkeleton />}
          {!loading && !data && <EmptyState />}
          {!loading && data && (
            <div className="space-y-4">
              {/* Summary */}
              <Card>
                <CardContent className="py-4">
                  <p className="text-sm text-muted-foreground">{data.summary}</p>
                  {data.uncovered_gaps.length > 0 && (
                    <div className="mt-3 flex items-center gap-2 text-xs text-amber-400">
                      <AlertCircle className="h-3.5 w-3.5" />
                      {data.uncovered_gaps.length} gap(s) couldn&apos;t be mapped to an enjoyable project — surfaced honestly.
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Recs grouped by gap */}
              {Array.from(recsByGap.entries()).map(([gap, recs], gi) => (
                <div key={gap} className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{gi + 1}</Badge>
                    <h3 className="text-sm font-semibold">{gap}</h3>
                    <Badge variant="secondary" className="text-[10px]">{recs.length} rec{recs.length > 1 ? "s" : ""}</Badge>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {recs.map((rec, i) => (
                      <RecCard key={i} rec={rec} delay={gi * 0.1 + i * 0.05} hasContext={data.has_personal_context} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="gaps">
          <Card>
            <CardContent className="py-4">
              {data ? (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">Canonical skill gaps from RecommendationService:</p>
                  <div className="flex flex-wrap gap-2">
                    {(data.gap_analysis.gaps ?? []).map((g) => (
                      <Badge key={g} variant="destructive">{g}</Badge>
                    ))}
                    {data.uncovered_gaps.map((g) => (
                      <Badge key={g} variant="warning">{g} (uncovered)</Badge>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Run the analysis to see skill gaps.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function RecCard({ rec, delay, hasContext }: { rec: Recommendation; delay: number; hasContext: boolean }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }}>
      <Card className="h-full overflow-hidden">
        <CardContent className="space-y-3 p-5">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500/30 to-cyan-500/30">
                <Lightbulb className="h-4 w-4 text-primary" />
              </div>
              <Badge variant="outline" className="text-[10px] capitalize">{rec.type}</Badge>
            </div>
            {hasContext && (
              <Badge variant="success" className="gap-1 text-[10px]">
                <Heart className="h-2.5 w-2.5" /> Personalized
              </Badge>
            )}
          </div>

          <div>
            <h4 className="text-sm font-semibold leading-tight">{rec.project_title}</h4>
            <p className="mt-1 text-xs text-muted-foreground">{rec.project_description}</p>
          </div>

          {rec.why_enjoyable && (
            <div className="rounded-lg bg-primary/5 p-2.5">
              <p className="flex items-start gap-1.5 text-xs text-primary">
                <Heart className="mt-0.5 h-3 w-3 shrink-0" />
                <span>{rec.why_enjoyable}</span>
              </p>
            </div>
          )}

          {rec.estimated_effort && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" /> {rec.estimated_effort}
            </div>
          )}

          {rec.learning_resources.length > 0 && (
            <div className="space-y-1">
              {rec.learning_resources.map((url, i) => (
                <a
                  key={i}
                  href={url.startsWith("http") ? url : `https://${url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-primary hover:underline"
                >
                  <BookOpen className="h-3 w-3" />
                  <span className="truncate">{url}</span>
                </a>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-secondary/40">
          <Target className="h-8 w-8 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium">Enter a Resume ID + Job ID to begin</p>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">
          The enjoyable-recommendations agent combines canonical skill gaps with your onboarding personal context.
        </p>
      </CardContent>
    </Card>
  );
}

function RecSkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {[0, 1, 2].map((i) => (
        <Card key={i}>
          <CardContent className="space-y-3 p-5">
            <div className="h-8 w-8 animate-pulse rounded-lg bg-secondary" />
            <div className="h-4 w-3/4 animate-pulse rounded bg-secondary" />
            <div className="h-12 w-full animate-pulse rounded bg-secondary/60" />
            <div className="h-8 w-full animate-pulse rounded bg-primary/10" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
