import { NextResponse, type NextRequest } from "next/server";
import { TOKEN_COOKIE } from "@/lib/api/server";

const PUBLIC_PATHS = ["/login", "/register"];
const AUTH_API = "/api/auth/";

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  // Never run on Next internals, static assets, or our own auth API routes.
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }
  const token = req.cookies.get(TOKEN_COOKIE)?.value;
  const isPublic = PUBLIC_PATHS.includes(pathname);
  const isRoot = pathname === "/";

  // Unauthenticated user hitting the app shell → login (preserve destination).
  if (!token && !isPublic && !isRoot) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }
  // Authenticated user on /login or root → dashboard.
  if (token && (isPublic || isRoot)) {
    const url = req.nextUrl.clone();
    // Onboarding redirect is decided client-side after /me fetch; here we go to dashboard.
    url.pathname = "/dashboard";
    url.search = "";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
