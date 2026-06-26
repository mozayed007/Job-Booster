import { API_URL, TOKEN_COOKIE, cookieOpts } from "@/lib/api/server";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const backend = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: body.email,
      password: body.password,
    }),
  });
  const data = await backend.json().catch(() => ({}));
  if (!backend.ok || !data.token) {
    return Response.json(
      { detail: data.detail ?? "Invalid credentials" },
      { status: backend.status || 401 }
    );
  }
  // Probe onboarding status to decide redirect target.
  let onboardingDone = false;
  try {
    const probe = await fetch(`${API_URL}/api/onboarding/profile`, {
      headers: { Authorization: `Bearer ${data.token}` },
    });
    if (probe.ok) {
      const j = (await probe.json()) as {
        personal_context?: unknown;
      };
      onboardingDone = Boolean(j.personal_context);
    }
  } catch {
    /* ignore — backend may not have onboarding yet */
  }
  // Token stays server-side: it lives only in the HttpOnly cookie and is never
  // returned to the browser. The app talks to the backend through /api/proxy/*.
  const res = Response.json({ onboarding_done: onboardingDone }, { status: 200 });
  res.headers.append("Set-Cookie", `${TOKEN_COOKIE}=${data.token};${cookieOpts()}`);
  return res;
}
