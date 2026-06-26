import { GradientBlobs } from "@/components/gradient-blobs";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen">
      <GradientBlobs />
      <div className="relative z-10 grid min-h-screen lg:grid-cols-2">
        {/* Marketing/visual side */}
        <div className="hidden flex-col justify-between p-12 lg:flex">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 glow-primary">
              <svg viewBox="0 0 24 24" className="h-5 w-5 text-white" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </div>
            <span className="text-lg font-bold tracking-tight">Job Booster</span>
          </div>

          <div className="max-w-md space-y-6">
            <h2 className="text-4xl font-bold leading-tight tracking-tight">
              Stop copy-pasting <span className="gradient-text">resumes.</span>
            </h2>
            <p className="text-muted-foreground">
              Feed it a resume and a job description. Get back a tailored resume,
              a cover letter, interview prep, and a tracked application — in
              seconds, not hours.
            </p>
            <div className="grid grid-cols-3 gap-4 pt-4">
              {[
                { stat: "9", label: "AI Agents" },
                { stat: "≤60s", label: "Per Package" },
                { stat: "100+", label: "LLM Models" },
              ].map((s) => (
                <div key={s.label} className="rounded-lg border border-border bg-card/40 p-3 text-center backdrop-blur-sm">
                  <div className="gradient-text text-2xl font-bold">{s.stat}</div>
                  <div className="text-[11px] text-muted-foreground">{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            Powered by Pydantic AI · LangChain · LiteLLM · FastAPI
          </p>
        </div>

        {/* Form side */}
        <div className="flex items-center justify-center p-6 sm:p-12">
          {children}
        </div>
      </div>
    </div>
  );
}
