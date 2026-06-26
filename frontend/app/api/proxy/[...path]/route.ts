import { NextRequest } from "next/server";
import {
  API_URL,
  TOKEN_COOKIE,
  getServerToken,
  clearCookieHeader,
} from "@/lib/api/server";

export const runtime = "nodejs";

/**
 * Same-origin JSON proxy to the backend. Reads the JWT from the HttpOnly cookie
 * and forwards it as a Bearer header, so the token never has to live in the
 * browser. On a 401 the cookie is cleared so the shell can bounce to /login.
 */
function unauthorized(): Response {
  const res = Response.json({ detail: "Session expired" }, { status: 401 });
  res.headers.append("Set-Cookie", clearCookieHeader(TOKEN_COOKIE));
  return res;
}

async function proxy(
  req: NextRequest,
  path: string[],
  method: string
): Promise<Response> {
  const token = await getServerToken();
  if (!token) return unauthorized();

  const inflight = new URL(req.url);
  const target = new URL(`${API_URL}/api/${path.join("/")}`);
  target.search = inflight.search;

  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  let body: BodyInit | undefined;
  if (method !== "GET" && method !== "HEAD") {
    const raw = await req.text();
    if (raw) {
      body = raw;
      headers["Content-Type"] =
        req.headers.get("content-type") ?? "application/json";
    }
  }

  const upstream = await fetch(target, { method, headers, body, cache: "no-store" });
  if (upstream.status === 401) return unauthorized();

  const text = await upstream.text();
  return new Response(text || null, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function GET(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params.path, "GET");
}

export async function POST(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params.path, "POST");
}

export async function PUT(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params.path, "PUT");
}
