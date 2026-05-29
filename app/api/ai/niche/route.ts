import { NextRequest } from "next/server";
import { analyzeNiche } from "@/lib/ai/generator";
import { auditLog } from "@/lib/audit";
import { getSession } from "@/lib/auth";
import { nicheSchema } from "@/lib/validators";
import { getClientIp, jsonError, rateLimit } from "@/lib/security";

export async function POST(request: NextRequest) {
  const session = await getSession();
  if (!session) {
    return jsonError("Unauthorized", 401);
  }

  const ip = getClientIp(request);
  const limit = rateLimit(`ai:${session.id}:${ip}`, 30, 60_000);
  if (!limit.ok) {
    return jsonError("Rate limit exceeded", 429);
  }

  const body = await request.json();
  const parsed = nicheSchema.safeParse(body);
  if (!parsed.success) {
    return jsonError("Invalid market", 422);
  }

  const analysis = analyzeNiche(parsed.data.market);
  await auditLog({
    userId: session.id,
    action: "niche.analyze",
    entity: "Niche",
    metadata: { market: parsed.data.market },
    ip
  });

  return Response.json({ analysis });
}
