import { TOKEN_COOKIE, clearCookieHeader } from "@/lib/api/server";

export const runtime = "nodejs";

export async function POST() {
  const res = new Response(JSON.stringify({ success: true }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
  res.headers.append("Set-Cookie", clearCookieHeader(TOKEN_COOKIE));
  return res;
}
