import { API_URL, TOKEN_COOKIE, cookieOpts } from "@/lib/api/server";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const backend = await fetch(`${API_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: body.email,
      password: body.password,
      name: body.name,
    }),
  });
  const data = await backend.json().catch(() => ({}));
  if (!backend.ok || !data.token) {
    return Response.json(
      { detail: data.detail ?? "Registration failed" },
      { status: backend.status || 400 }
    );
  }
  // New users never have onboarding context. Token never reaches the browser.
  const res = Response.json({ onboarding_done: false }, { status: 200 });
  res.headers.append("Set-Cookie", `${TOKEN_COOKIE}=${data.token};${cookieOpts()}`);
  return res;
}
