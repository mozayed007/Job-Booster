"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  MessageSquareHeart,
  Send,
  Sparkles,
  Save,
  Loader2,
  ShieldCheck,
  Code2,
 Download,
  CheckCircle2,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { SegmentedProgress } from "@/components/segmented-progress";
import { cn } from "@/lib/utils";
import type { ChatTurn, PersonalProfileOutput } from "@/lib/types";

const EMPTY_PROFILE: PersonalProfileOutput = {
  hobbies: [],
  interests: [],
  free_time_activities: [],
  favorite_tech_or_domains: [],
  work_style: "",
  short_bio: "",
  raw_transcript: "",
};

function OnboardingContent() {
  const router = useRouter();
  const params = useSearchParams();
  const isNew = params.get("new") === "1";

  const [history, setHistory] = React.useState<ChatTurn[]>([]);
  const [input, setInput] = React.useState("");
  const [ready, setReady] = React.useState(false);
  const [chatLoading, setChatLoading] = React.useState(false);
  const [started, setStarted] = React.useState(false);

  // Profile panel
  const [savedProfile, setSavedProfile] = React.useState<PersonalProfileOutput | null>(null);
  const [jsonOpen, setJsonOpen] = React.useState(false);
  const [jsonText, setJsonText] = React.useState("");
  const [savingJson, setSavingJson] = React.useState(false);

  const scrollRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: 1e9, behavior: "smooth" });
  }, [history, chatLoading]);

  // Initial greeting from history if any. Otherwise, user clicks "Start chat".
  // On mount, load any saved profile.
  React.useEffect(() => {
    void loadProfile();
  }, []);

  // Auto-start for brand-new users (from /register or /login?onboarding_done=false)
  React.useEffect(() => {
    if (isNew && !started && savedProfile === null) {
      void startChat();
    }
  }, [isNew, started, savedProfile]);

  async function loadProfile() {
    try {
      const res = await fetch("/api/proxy/onboarding/profile");
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (res.ok) {
        const data = (await res.json()) as { personal_context: PersonalProfileOutput | null };
        if (data.personal_context) {
          setSavedProfile(data.personal_context);
          setJsonText(JSON.stringify(data.personal_context, null, 2));
        }
      }
    } catch {
      /* backend may be down during demo */
    }
  }

  async function sendToBackend(
    msg: string,
    hist: ChatTurn[]
  ): Promise<{ ready: boolean; history: ChatTurn[] } | null> {
    try {
      const res = await fetch("/api/proxy/onboarding/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_message: msg, history: hist }),
      });
      if (res.status === 401) {
        toast.error("Please log in again");
        window.location.href = "/login";
        return null;
      }
      if (!res.ok) {
        const j = (await res.json().catch(() => ({}))) as { detail?: string };
        toast.error(j.detail ?? "Chat failed");
        return null;
      }
      const d = (await res.json()) as { profile_ready: boolean; history: ChatTurn[] };
      return { ready: d.profile_ready, history: d.history };
    } catch {
      toast.error("Network error — is the API running?");
      return null;
    }
  }

  async function startChat() {
    setStarted(true);
    setChatLoading(true);
    const result = await sendToBackend("Hi, I'd like to get started.", []);
    setChatLoading(false);
    if (!result) return;
    setHistory(result.history);
    setReady(result.ready);
  }

  async function sendMessage() {
    if (!input.trim() || chatLoading) return;
    const userMsg = input;
    setInput("");
    setChatLoading(true);
    const result = await sendToBackend(userMsg, history);
    setChatLoading(false);
    if (!result) return;
    setHistory(result.history);
    setReady(result.ready);
  }

  async function finalize() {
    if (history.length === 0) return;
    setChatLoading(true);
    try {
      const res = await fetch("/api/proxy/onboarding/finalize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_message: "", history }),
      });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        const j = (await res.json().catch(() => ({}))) as { detail?: string };
        toast.error(j.detail ?? "Finalize failed");
        return;
      }
      const data = (await res.json()) as { personal_context: PersonalProfileOutput };
      setSavedProfile(data.personal_context);
      setJsonText(JSON.stringify(data.personal_context, null, 2));
      toast.success("Profile saved! Recommendations will be personalized now.");
      router.push("/recommendations");
    } catch {
      toast.error("Network error");
    } finally {
      setChatLoading(false);
    }
  }

  async function saveJson() {
    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonText);
    } catch {
      toast.error("Invalid JSON");
      return;
    }
    setSavingJson(true);
    try {
      const res = await fetch("/api/proxy/onboarding/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: parsed }),
      });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        const j = (await res.json().catch(() => ({}))) as { detail?: string };
        toast.error(j.detail ?? "Save failed");
        return;
      }
      const data = (await res.json()) as { personal_context: PersonalProfileOutput };
      setSavedProfile(data.personal_context);
      toast.success("Profile updated");
    } catch {
      toast.error("Network error");
    } finally {
      setSavingJson(false);
    }
  }

  const progress = savedProfile
    ? [
        savedProfile.hobbies.length,
        savedProfile.interests.length,
        savedProfile.free_time_activities.length,
        savedProfile.favorite_tech_or_domains.length,
        savedProfile.work_style ? 1 : 0,
      ].filter((n) => n > 0).length
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Onboarding"
        description="A short, friendly chat to learn what you enjoy — so skill-gap recommendations feel personal"
        icon={MessageSquareHeart}
        actions={
          savedProfile ? (
            <Badge variant="success" className="gap-1">
              <CheckCircle2 className="h-3 w-3" /> Profile saved
            </Badge>
          ) : (
            <Badge variant="warning">Not yet personalized</Badge>
          )
        }
      />

      {/* Isolation promise banner */}
      <Card className="border-emerald-500/30 bg-emerald-500/5">
        <CardContent className="flex items-center gap-3 py-3">
          <ShieldCheck className="h-5 w-5 shrink-0 text-emerald-400" />
          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Privacy promise:</span>{" "}
            Used <em>only</em> by the gap-recommendation agent to suggest enjoyable
            projects/courses. Your resume, cover-letter, and CV agents{" "}
            <span className="font-medium text-foreground">never</span> read this —
            zero fabricated bullets.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chat */}
        <div className="lg:col-span-2">
          <Card className="flex h-[600px] flex-col">
            <CardHeader className="border-b border-border py-4">
              <CardTitle className="flex items-center gap-2 text-base">
                <Sparkles className="h-4 w-4 text-primary" />
                Onboarding Interview
              </CardTitle>
            </CardHeader>

            <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
              {history.length === 0 && !chatLoading && (
                <div className="flex h-full flex-col items-center justify-center text-center">
                  <motion.div
                    animate={{ scale: [1, 1.05, 1] }}
                    transition={{ duration: 3, repeat: Infinity }}
                    className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 glow-primary"
                  >
                    <MessageSquareHeart className="h-8 w-8 text-white" />
                  </motion.div>
                  <p className="mb-1 text-sm font-medium">Let&apos;s get personal</p>
                  <p className="mb-4 max-w-xs text-xs text-muted-foreground">
                    ~90 seconds. I&apos;ll ask about your hobbies, interests, and work style.
                  </p>
                  <Button onClick={startChat} variant="gradient" disabled={chatLoading}>
                    <Sparkles className="h-4 w-4" /> Start chat
                  </Button>
                </div>
              )}

              <AnimatePresence initial={false}>
                {history.map((turn, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                      "flex gap-3",
                      turn.role === "user" ? "justify-end" : "justify-start"
                    )}
                  >
                    {turn.role === "assistant" && (
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-500">
                        <Sparkles className="h-4 w-4 text-white" />
                      </div>
                    )}
                    <div
                      className={cn(
                        "max-w-[80%] rounded-2xl px-4 py-2 text-sm",
                        turn.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary text-secondary-foreground"
                      )}
                    >
                      {turn.content}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {chatLoading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-500">
                    <Sparkles className="h-4 w-4 text-white" />
                  </div>
                  <div className="flex gap-1">
                    {[0, 1, 2].map((d) => (
                      <motion.span
                        key={d}
                        className="h-2 w-2 rounded-full bg-primary"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1, delay: d * 0.2, repeat: Infinity }}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-border p-4">
              {ready && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="mb-3 flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Enough context gathered! Click Save to finalize.
                </motion.div>
              )}
              <div className="flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void sendMessage();
                    }
                  }}
                  placeholder={history.length === 0 ? "Click Start chat…" : "Type your answer…"}
                  disabled={!started || chatLoading}
                />
                <Button onClick={sendMessage} disabled={!input.trim() || chatLoading || !started} size="icon">
                  {chatLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </Button>
              </div>
              <div className="mt-2 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={finalize}
                  disabled={!ready || chatLoading || history.length === 0}
                  className="gap-1.5"
                >
                  <Save className="h-3.5 w-3.5" /> Save profile
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Profile panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Saved Profile</CardTitle>
              <div className="mt-2">
                <SegmentedProgress value={progress} max={5} />
                <p className="mt-1 text-[11px] text-muted-foreground">{progress}/5 areas covered</p>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {savedProfile ? (
                <>
                  <ProfileField label="Hobbies" values={savedProfile.hobbies} />
                  <ProfileField label="Interests" values={savedProfile.interests} />
                  <ProfileField label="Free-time activities" values={savedProfile.free_time_activities} />
                  <ProfileField label="Favorite tech / domains" values={savedProfile.favorite_tech_or_domains} />
                  {savedProfile.work_style && (
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-muted-foreground">Work style</p>
                      <p className="text-sm">{savedProfile.work_style}</p>
                    </div>
                  )}
                  {savedProfile.short_bio && (
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-muted-foreground">Short bio</p>
                      <p className="text-sm">{savedProfile.short_bio}</p>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-xs text-muted-foreground">
                  No personal context saved yet. Run the chat interview →
                </p>
              )}
            </CardContent>
          </Card>

          {/* Advanced: raw JSON editor */}
          <Collapsible open={jsonOpen} onOpenChange={setJsonOpen}>
            <Card>
              <CollapsibleTrigger asChild>
                <button className="flex w-full items-center justify-between p-4 hover:bg-secondary/40">
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <Code2 className="h-4 w-4 text-muted-foreground" />
                    Advanced: edit raw profile JSON
                  </span>
                  <Badge variant="outline" className="text-[10px]">PUT /onboarding/profile</Badge>
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="space-y-3 border-t border-border p-4">
                  <Textarea
                    value={jsonText}
                    onChange={(e) => setJsonText(e.target.value)}
                    placeholder={JSON.stringify(EMPTY_PROFILE, null, 2)}
                    className="min-h-[200px] font-mono text-xs"
                  />
                  <div className="flex gap-2">
                    <Button onClick={saveJson} disabled={savingJson} size="sm" variant="gradient">
                      {savingJson ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                      Apply
                    </Button>
                    <Button
                      onClick={loadProfile}
                      variant="outline"
                      size="sm"
                    >
                      <Download className="h-3.5 w-3.5" /> Load current
                    </Button>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Server validates against <code className="text-primary">PersonalProfileOutput</code> and returns 422 on a bad shape.
                  </p>
                </div>
              </CollapsibleContent>
            </Card>
          </Collapsible>
        </div>
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <React.Suspense
      fallback={
        <div className="flex h-96 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <OnboardingContent />
    </React.Suspense>
  );
}

function ProfileField({ label, values }: { label: string; values: string[] }) {
  if (!values?.length) return null;
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1">
        {values.map((v, i) => (
          <Badge key={i} variant="secondary" className="font-normal">{v}</Badge>
        ))}
      </div>
    </div>
  );
}
