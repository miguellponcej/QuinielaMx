import { NextRequest, NextResponse } from "next/server";

const publicPrefixes = [
  "/login",
  "/l/",
  "/checkout",
  "/api/auth",
  "/api/checkout",
  "/api/stripe/webhook",
  "/api/download",
  "/_next",
  "/favicon.ico"
];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublic = publicPrefixes.some((prefix) => pathname.startsWith(prefix));

  if (isPublic) {
    return NextResponse.next();
  }

  const hasSession = request.cookies.has("adpmm_session");

  if (!hasSession && pathname.startsWith("/api")) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!hasSession) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!.*\\..*).*)"]
};
