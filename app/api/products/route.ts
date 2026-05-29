import { NextRequest } from "next/server";
import { auditLog } from "@/lib/audit";
import { getSession } from "@/lib/auth";
import { createGeneratedProduct } from "@/lib/repository";
import { getClientIp, jsonError, rateLimit } from "@/lib/security";
import { productCreateSchema } from "@/lib/validators";

export async function POST(request: NextRequest) {
  const session = await getSession();
  if (!session) {
    return jsonError("Unauthorized", 401);
  }

  const ip = getClientIp(request);
  const limit = rateLimit(`product:${session.id}:${ip}`, 20, 60_000);
  if (!limit.ok) {
    return jsonError("Rate limit exceeded", 429);
  }

  const body = await request.json();
  const parsed = productCreateSchema.safeParse(body);

  if (!parsed.success) {
    return jsonError("Invalid product input", 422);
  }

  const result = await createGeneratedProduct(session.id, parsed.data);

  await auditLog({
    userId: session.id,
    action: "product.create",
    entity: "Product",
    entityId: result.product.id,
    metadata: { title: result.product.title },
    ip
  });

  return Response.json(result);
}
