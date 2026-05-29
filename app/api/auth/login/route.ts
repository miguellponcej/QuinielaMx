import { NextRequest, NextResponse } from "next/server";
import { createSessionToken, SESSION_COOKIE, verifyAdminCredentials } from "@/lib/auth";
import { getClientIp, jsonError, rateLimit } from "@/lib/security";

export async function POST(request: NextRequest) {
  const ip = getClientIp(request);
  const limit = rateLimit(`login:${ip}`, 5, 60_000);

  if (!limit.ok) {
    return jsonError("Too many attempts", 429);
  }

  const body = (await request.json()) as { email?: string; password?: string };
  const email = body.email?.trim() ?? "";
  const password = body.password ?? "";

  if (!verifyAdminCredentials(email, password)) {
    return jsonError("Invalid credentials", 401);
  }

  const token = createSessionToken({
    id: "admin",
    email,
    name: email.split("@")[0] ?? "Owner"
  });

  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 12
  });

  return response;
}
