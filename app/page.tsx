import { redirect } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { ProductStudio } from "@/components/product-studio";
import { getSession } from "@/lib/auth";
import { getDashboardSnapshot } from "@/lib/repository";

export default async function DashboardPage() {
  const session = await getSession();

  if (!session) {
    redirect("/login");
  }

  const snapshot = await getDashboardSnapshot(session.id);

  return (
    <AppShell user={session}>
      <ProductStudio initialSnapshot={snapshot} />
    </AppShell>
  );
}
