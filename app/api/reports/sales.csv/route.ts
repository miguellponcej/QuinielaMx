import { getSession } from "@/lib/auth";
import { ordersToCsv } from "@/lib/csv";
import { getDashboardSnapshot } from "@/lib/repository";
import { jsonError } from "@/lib/security";

export async function GET() {
  const session = await getSession();
  if (!session) {
    return jsonError("Unauthorized", 401);
  }

  const snapshot = await getDashboardSnapshot(session.id);
  const csv = ordersToCsv(snapshot.orders);

  return new Response(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": 'attachment; filename="sales-report.csv"'
    }
  });
}
