import { cookies } from "next/headers";
import { API_URL, TOKEN_COOKIE, clearCookieHeader } from "@/lib/api/server";

export const runtime = "nodejs";

export async function GET() {
  const jar = await cookies();
  const token = jar.get(TOKEN_COOKIE)?.value;
  if (!token) return Response.json({ user: null }, { status: 401 });
  try {
    const r = await fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!r.ok) {
      // Expired/invalid token: clear the stale cookie so the user can reach
      // /login (middleware admits on cookie presence; we must invalidate it).
      const res = Response.json({ user: null }, { status: r.status });
      if (r.status === 401) res.headers.append("Set-Cookie", clearCookieHeader(TOKEN_COOKIE));
      return res;
    }
    const data = (await r.json()) as {
      user: {
        id: number;
        email: string;
        name: string;
        profile_json: Record<string, unknown> | null;
      };
    };
    return Response.json(data);
  } catch {
    return Response.json({ user: null }, { status: 500 });
  }
}
