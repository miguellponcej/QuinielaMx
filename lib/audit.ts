import { hasUsableDatabaseUrl, prisma } from "@/lib/db";
import type { Prisma } from "@prisma/client";

export async function auditLog(input: {
  userId?: string;
  action: string;
  entity: string;
  entityId?: string;
  metadata?: Record<string, unknown>;
  ip?: string;
}) {
  if (!hasUsableDatabaseUrl()) {
    return;
  }

  try {
    const data: Prisma.AuditLogUncheckedCreateInput = {
      userId: input.userId,
      action: input.action,
      entity: input.entity,
      entityId: input.entityId,
      metadata: input.metadata as Prisma.InputJsonValue,
      ip: input.ip
    };

    await prisma.auditLog.create({
      data
    });
  } catch {
    // Audit logging should not break the user-facing flow.
  }
}
